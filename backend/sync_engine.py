from typing import List
from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.models import Stock, PortfolioSnapshot
from backend.database import engine
from backend.adapters.zerodha import ZerodhaAdapter
from backend.adapters.vested import VestedAdapter
from datetime import datetime, timedelta
from backend.logger import logger

class SyncEngine:
    def __init__(self):
        # Adapters handle their own credential loading from Env or DB
        self.adapters = [
            ZerodhaAdapter(),
            VestedAdapter()
        ]

    async def run_sync(self):
        """
        Executes the sync process in a separate thread to avoid blocking the event loop.
        """
        import asyncio
        return await self._execute_sync()

    async def _execute_sync(self):
        import asyncio
        all_stocks: List[Stock] = []
        
        # 1. Fetch from all adapters
        for adapter in self.adapters:
            try:
                await asyncio.to_thread(adapter.authenticate)
                stocks = await asyncio.to_thread(adapter.fetch_holdings)
                all_stocks.extend(stocks)
            except Exception as e:
                print(f"Error syncing adapter {adapter}: {e}")

        # 1.1 Fetch Manual Stocks from DB to ensure they get price updates
        try:
             async with AsyncSession(engine) as temp_session:
                 manual_stocks = (await temp_session.exec(select(Stock).where(Stock.platform == "manual"))).all()
                 for ms in manual_stocks:
                     # Detach from session so we can modify and re-add in main session
                     temp_session.sync_session.expunge(ms)
                     all_stocks.append(ms)
        except Exception as e:
             print(f"Error fetching manual stocks: {e}")

        # 1.5 Fetch current prices from reputed source (Yahoo Finance)
        # This overwrites the price from the broker with the latest market price
        try:
            from backend.services.price_fetcher import PriceFetcher
            fetcher = PriceFetcher()
            await asyncio.to_thread(fetcher.update_prices, all_stocks)
        except Exception as e:
            print(f"Error fetching external prices: {e}")

        # 2. Update Database
        async with AsyncSession(engine) as session:
            # For simplicity in this demo, we can clear old stocks and re-insert
            # Or use upsert logic. Clearing is safer to avoid duplicates if ID isn't stable across syncs.
            # In a real produciton app, we would match by symbol+platform and update.
            # Smart Update Strategy to preserve IDs and Theme relations
            # 1. Get all existing stocks
            existing_stocks = (await session.exec(select(Stock))).all()
            existing_map = {(s.symbol, s.platform): s for s in existing_stocks}
            
            # set of (symbol, platform) that we have processed in this sync
            processed_keys = set()
            
            total_value_inr = 0.0
            
            for stock_data in all_stocks:
                key = (stock_data.symbol, stock_data.platform)
                processed_keys.add(key)
                
                # Calculate value for snapshot
                value = stock_data.quantity * stock_data.current_price
                if stock_data.currency == "USD":
                     # Use live rate
                    from backend.services.currency_service import CurrencyService
                    rate = await asyncio.to_thread(CurrencyService().get_usd_inr_rate)
                    value *= rate
                total_value_inr += value
                
                if key in existing_map:
                    # Update existing stock
                    db_stock = existing_map[key]
                    
                    # Change Detection for AI analysis
                    # If price change > 1%, mark for re-analysis by clearing last_analyzed
                    if db_stock.current_price > 0:
                        price_diff = abs(stock_data.current_price - db_stock.current_price) / db_stock.current_price
                        if price_diff > 0.01: # 1% threshold
                             db_stock.last_analyzed = None 
                             logger.info(f"Flagging {db_stock.symbol} for re-analysis (Price change: {price_diff*100:.1f}%)")

                    db_stock.quantity = stock_data.quantity
                    db_stock.current_price = stock_data.current_price
                    db_stock.previous_close = stock_data.previous_close
                    db_stock.average_price = stock_data.average_price
                    db_stock.name = stock_data.name 
                    db_stock.last_synced = stock_data.last_synced
                    db_stock.weekly_change_percentage = stock_data.weekly_change_percentage
                    db_stock.asset_class = stock_data.asset_class 
                    session.add(db_stock)
                else:
                    # Insert new stock
                    session.add(stock_data)

            # 3. Optional: Remove stocks that are no longer in portfolio
            # Only if we are sure the successful sync covers ALL platforms.
            # If one adapter failed, we shouldn't delete its stocks. 
            # We assume here that if we got ANY results, we processed them.
            # But wait, if Zerodha syncs but Vested fails, we shouldn't delete Vested stocks.
            # We can check which adapters succeeded? 
            # ideally we only delete stocks belonging to platforms we successfully synced.
            # For this MVP, let's just keep old stocks or delete only if we are sure.
            # Let's delete stocks from platforms we encountered in all_stocks (i.e. if we saw at least one stock from 'zerodha', we assume we got full list)
            # Or better: check processed_keys.
            
            # 3. Optional: Remove stocks that are no longer in portfolio
            synced_platforms = set(s.platform for s in all_stocks)
            
            for key, db_stock in existing_map.items():
                if key not in processed_keys and db_stock.platform in synced_platforms:
                    await session.delete(db_stock)

            # Create Snapshot
            snapshot = PortfolioSnapshot(total_value_inr=total_value_inr)
            session.add(snapshot)
            
            await session.commit()
            
        return {"status": "success", "synced_count": len(all_stocks)}
