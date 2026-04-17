"""
Analysis Engine - Portfolio Performance Analysis and Event Detection

This module provides analytical capabilities for the stock portfolio dashboard:
- Calculates performance metrics for investment themes/baskets
- Identifies top performing and underperforming stocks
- Detects significant price movements and creates timeline events
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlmodel import Session, select
from backend.models import Stock, Theme, TimelineEvent
from backend.database import engine
from backend.logger import logger


class AnalysisEngine:
    """
    Core analysis engine for portfolio insights and performance tracking.
    
    Provides methods for:
    - Theme/basket performance calculation
    - Winner/loser identification
    - Significant event detection
    """
    
    def __init__(self, session: Session):
        """
        Initialize the analysis engine with a database session.
        
        Args:
            session: SQLModel database session for querying and persisting data
        """
        self.session = session

    def calculate_basket_performance(self) -> List[Dict[str, Any]]:
        """
        Calculate performance metrics for each investment theme/basket.
        
        Computes total value, absolute returns, and percentage returns for each theme
        by aggregating all stocks within that theme. Handles multi-currency portfolios
        with basic USD to INR conversion.
        
        Returns:
            List of dictionaries containing:
                - theme_id: Unique theme identifier
                - name: Theme name
                - total_value: Current value in INR
                - return_abs: Absolute return (current - invested)
                - return_pct: Percentage return ((current - invested) / invested * 100)
        """
        # Fetch all themes from database
        themes = self.session.exec(select(Theme)).all()
        results = []
        
        for theme in themes:
            total_invested = 0.0  # Total amount invested in this theme
            current_value = 0.0   # Current market value of this theme
            
            # Get live rate
            from backend.services.currency_service import CurrencyService
            usd_rate = CurrencyService().get_usd_inr_rate()
            
            # Aggregate values from all stocks in the theme
            for stock in theme.stocks:
                # Currency conversion: USD to INR
                rate = usd_rate if stock.currency == "USD" else 1.0
                
                # Calculate invested amount: quantity × average purchase price
                invested = stock.quantity * stock.average_price * rate
                
                # Calculate current value: quantity × current market price
                curr = stock.quantity * stock.current_price * rate
                
                total_invested += invested
                current_value += curr
                
            # Calculate returns
            if total_invested > 0:
                # Absolute return: how much money gained/lost
                abs_return = current_value - total_invested
                
                # Percentage return: return as percentage of investment
                pct_return = (abs_return / total_invested) * 100
            else:
                # Handle edge case of zero investment
                abs_return = 0.0
                pct_return = 0.0
                
            # Build result object for this theme
            results.append({
                "theme_id": theme.id,
                "name": theme.name,
                "total_value": current_value,
                "return_abs": abs_return,
                "return_pct": pct_return
            })
            
        return results

    async def generate_insights(self) -> Dict[str, Any]:
        """
        Generate portfolio insights by identifying winners and losers.
        
        Analyzes all stocks to determine top and bottom performers based on
        percentage change from average price.
        
        Returns:
            Dictionary containing:
                - winners: Top 3 performing stocks with reasons
                - losers: Bottom 3 performing stocks with reasons
        """
        # Fetch all stocks from database
        stocks = self.session.exec(select(Stock)).all()
        
        # Calculate performance for each stock
        # Note: Using (current - average) / average as proxy for performance
        # In production, use actual daily change from market data API
        stock_performance = []
        for stock in stocks:
            # V9: Use Weekly Change if available, else 0
            pct_change = stock.weekly_change_percentage if stock.weekly_change_percentage is not None else 0.0
            
            stock_performance.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "pct_change": pct_change,
                "current_price": stock.current_price
            })
            
        # Sort stocks by performance (best to worst)
        stock_performance.sort(key=lambda x: x["pct_change"], reverse=True)
        
        # Extract top 3 winners and bottom 3 losers
        winners = stock_performance[:3]
        losers = stock_performance[-3:]
        
        # Add explanatory reasons using LLM
        # In production, this uses Perplexity via LLMService
        
        # We need LLMService here. Since it's not passed in init, we instantiate it
        # This draws api_key from DB Config
        from backend.models import Config
        from backend.llm_service import LLMService
        from backend.services.scraper import NewsScraperService as Scraper
        
        scraper = Scraper()
        
        from backend.security import get_api_key
        api_key = get_api_key(self.session, "perplexity_api_key")
        llm = LLMService(api_key=api_key)

        async def _enrich_with_reason(item):
            if api_key:
                # [DEEP INTEL] Fetch comprehensive intelligence
                try:
                    deep_data = await scraper.fetch_comprehensive_intelligence(item["symbol"], llm)
                    
                    deep_context = f"""
                    [POLITICAL/GEO] {deep_data.get('political', 'N/A')}
                    [MACRO] {deep_data.get('macro', 'N/A')}
                    """
                except Exception as e:
                    print(f"Deep Intel Error for {item['symbol']}: {e}")
                    deep_context = None

                res = llm.analyze_stock_movement(item["symbol"], item["pct_change"], deep_context=deep_context)
                item["reason"] = res["reason"]
                item["citations"] = res["citations"]
            else:
                item["reason"] = "Strong movement (Configure AI for detailed reason)."
                item["citations"] = []

        for w in winners:
             await _enrich_with_reason(w)
            
        for l in losers:
             await _enrich_with_reason(l)
            
        return {
            "winners": winners,
            "losers": losers
        }


    async def detect_significant_events(self):
        """
        Detect and record significant price movements as timeline events.
        
        Scans all stocks for price changes exceeding 5% from average price.
        Creates TimelineEvent entries for significant movements to populate
        the portfolio timeline/feed.
        
        Note: Uses variance from average price as proxy. In production, use
        actual day-over-day or intraday price changes from market data.
        
        Side effects:
            - Creates TimelineEvent records in database
            - Commits changes to database
        """
        
        from backend.models import Config
        from backend.llm_service import LLMService

        # Fetch all stocks
        stocks = self.session.exec(select(Stock)).all()
        
        # Init LLM
        from backend.security import get_api_key
        api_key = get_api_key(self.session, "perplexity_api_key")
        llm = LLMService(api_key=api_key)
        
        # Instantiate Scraper for Deep Intel
        from backend.services.scraper import NewsScraperService as Scraper
        scraper = Scraper()
        
        for stock in stocks:
            # Calculate percentage change from average purchase price
            # Using current vs prev_close if available for daily events, else avg for overall
            # Actually, Timeline usually implies "Just happened", so let's stick to day change if possible.
            # But the original code used avg price. I'll switch to Day Change if prev_close exists.
            
            pct_change = 0.0
            if stock.previous_close:
                 pct_change = ((stock.current_price - stock.previous_close) / stock.previous_close) * 100
            else:
                 pct_change = ((stock.current_price - stock.average_price) / stock.average_price) * 100
            
            # Check if change is significant (>3% threshold for daily)
            if abs(pct_change) > 3.0:
                # Prevent duplicate events for TODAY
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                
                existing = self.session.exec(select(TimelineEvent).where(
                    TimelineEvent.related_stock_symbol == stock.symbol
                ).where(TimelineEvent.date >= today_start)).first()
                
                if not existing:
                    # Determine if price surged (positive) or plunged (negative)
                    direction = "surged" if pct_change > 0 else "plunged"
                    
                    # Generate specific reason via LLM
                    description = f"{stock.name} saw significant movement."
                    citations_json = None
                    if api_key:
                        try:
                            # 2. Fetch News & Deep Intelligence
                            news = await scraper.fetch_news(stock.symbol)
                            
                            # [NEW] Deep Intelligence Fetch
                            deep_data = await scraper.fetch_comprehensive_intelligence(stock.symbol, llm)
                            deep_context = f"""
                            [POLITICAL/GEO] {deep_data.get('political', 'N/A')}
                            [MACRO] {deep_data.get('macro', 'N/A')}
                            """
                            
                            res = llm.analyze_stock_movement(stock.symbol, pct_change, news=news, deep_context=deep_context)
                            description = res["reason"]
                            import json
                            if res["citations"]:
                                citations_json = json.dumps(res["citations"])
                        except Exception as e: # Catch specific exception if possible, or log it
                            print(f"Error generating LLM reason for {stock.symbol}: {e}")
                            pass
                    
                    # Create timeline event
                    event = TimelineEvent(
                        title=f"{stock.symbol} {direction} by {pct_change:.1f}%",
                        description=description,
                        impact_percent=pct_change,
                        related_stock_symbol=stock.symbol,
                        date=datetime.utcnow(),
                        references=citations_json
                    )
                    self.session.add(event)

                    
        # Persist all events to database
        self.session.commit()

    async def refresh_news(self):
        """
        Fetch fresh news for all stocks in the portfolio.
        
        Refactored from SyncEngine to ensure separation of concerns.
        Includes deduplication (URL-based) and freshness checks (<30 days).
        """
        from backend.services.scraper import NewsScraperService as Scraper
        from backend.models import NewsArticle
        
        logger.info("Starting News Refresh...")
        scraper = Scraper()
        
        # Get all stocks to fetch news for
        stocks = self.session.exec(select(Stock)).all()
        
        articles_added = 0
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Track URLs seen in this session to prevent duplicate inserts before commit
        # (Though we flush per stock or batch, keeping track helps)
        seen_urls = set()

        for stock in stocks:
            try:
                # Async fetch
                news_items = await scraper.fetch_news(stock.symbol)
                
                stock_articles_count = 0
                for item in news_items:
                    url = item.get("link", "")
                    if not url or url == "#" or url in seen_urls:
                        continue
                        
                    # Date Check
                    pub_time = datetime.fromtimestamp(item.get("providerPublishTime", 0)) if item.get("providerPublishTime") else datetime.utcnow()
                    if pub_time < cutoff_date:
                        continue

                    # Deduplicate by URL against DB
                    # (This might be slow for many articles, but necessary for uniqueness)
                    exists = self.session.exec(select(NewsArticle).where(NewsArticle.url == url)).first()
                    if not exists:
                        article = NewsArticle(
                            stock_id=stock.id,
                            title=item.get("title", "") or "No Title",
                            url=url,
                            source=item.get("publisher") or "Unknown",
                            published_date=pub_time,
                            summary=f"News related to {stock.symbol}",
                            sentiment="neutral" 
                        )
                        self.session.add(article)
                        seen_urls.add(url)
                        stock_articles_count += 1
                        articles_added += 1
                
                if stock_articles_count > 0:
                     logger.info(f"Added {stock_articles_count} new articles for {stock.symbol}")

            except Exception as e:
                logger.error(f"Failed to sync news for {stock.symbol}: {e}")
        
        try:
            self.session.commit()
            logger.info(f"News Refresh Complete. Total new articles: {articles_added}")
        except Exception as e:
            logger.error(f"News commit error: {e}")
            self.session.rollback()
            
        return {"articles_added": articles_added}
