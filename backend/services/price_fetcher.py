import yfinance as yf
from typing import List, Tuple, Optional
from backend.models import Stock
from backend.logger import logger
import time

class PriceFetcher:
    def __init__(self):
        # Yfinance handles headers internally
        pass
        
    def update_prices(self, stocks: List[Stock]) -> None:
        """
        Updates the current_price and previous_close of stocks in-place using yfinance.
        """
        if not stocks:
            return

        logger.info(f"Fetching external prices for {len(stocks)} stocks via yfinance...")
        
        for stock in stocks:
            try:
                # 1. Map Symbol
                yahoo_symbol = self._get_yahoo_symbol(stock)
                
                # 2. Fetch Data
                ticker = yf.Ticker(yahoo_symbol)
                
                # Use fast_info for latest price metadata (faster/reliable than .info)
                # Note: fast_info keys: last_price, previous_close, year_high, etc.
                try:
                    price = ticker.fast_info.last_price
                    prev_close = ticker.fast_info.previous_close
                except:
                    # Fallback to history if fast_info fails (sometimes happens on weak conn)
                    hist = ticker.history(period="2d")
                    if not hist.empty:
                         price = hist['Close'].iloc[-1]
                         prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else price
                    else:
                         price = None
                         prev_close = None

                if price:
                    old_price = stock.current_price
                    stock.current_price = price
                    logger.info(f"Updated price for {stock.symbol}: {old_price} -> {price}")
                
                if prev_close:
                    stock.previous_close = prev_close
                    # logger.info(f"Updated prev_close for {stock.symbol}: {prev_close}")
                
                # 3. Weekly Change (Already yfinance)
                weekly_pct = self._fetch_weekly_change_yf(stock, ticker)
                if weekly_pct is not None:
                     stock.weekly_change_percentage = weekly_pct
                     # logger.info(f"Updated weekly change for {stock.symbol}: {weekly_pct:.2f}%")
                    
                # Rate limit politeness not strictly needed for yfinance wrapper but good practice
                # time.sleep(0.1) 
                
            except Exception as e:
                logger.error(f"Error fetching data for {stock.symbol}: {e}")

    def _get_yahoo_symbol(self, stock: Stock) -> str:
        """Helper to format symbol for Yahoo Finance"""
        symbol = stock.symbol.upper()
        
        # Crypto Logic
        if stock.asset_class == "CRYPTO":
            # If already has hyphen (e.g. BTC-USD), assume correct
            if "-" in symbol:
                return symbol
            
            # Auto-append currency suffix
            # Default to -USD if currency is USD, or if INR (usually INR pairs exist but USD is liquid)
            # Actually, yfinance has BTC-INR. Let's respect the currency field.
            return f"{symbol}-{stock.currency.upper()}"

        # Existing Stock Logic
        if stock.platform == "zerodha" or stock.currency == "INR":
            if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
                return f"{symbol}.NS"
        return symbol

    def _fetch_weekly_change_yf(self, stock: Stock, ticker: yf.Ticker) -> Optional[float]:
        """Fetch 5-day percentage change using existing ticker obj"""
        try:
            hist = ticker.history(period="5d")
            
            if not hist.empty and len(hist) >= 2:
                # Use Close price
                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                
                if start_price and start_price > 0:
                    pct_change = ((end_price - start_price) / start_price) * 100
                    return pct_change
                    
        except Exception as e:
            logger.error(f"Error fetching weekly data for {stock.symbol}: {e}")
            
        return None
