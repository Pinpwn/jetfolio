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
from backend.models import Stock, Theme, TimelineEvent, Config
from backend.database import engine
from backend.logger import logger
from backend.security import get_secure_config
from backend.llm_service import LLMService

def get_llm_service(session: Session) -> LLMService:
    """
    Helper to initialize LLMService with configured provider and credentials.
    Priority: Environment Variables > Encrypted Database Config.
    """
    import os
    from backend.security import get_api_key
    
    # 1. Determine Provider
    provider = os.getenv("LLM_PROVIDER")
    if not provider:
        config_provider = session.get(Config, "llm_provider")
        provider = get_secure_config().get_value(config_provider) if config_provider else "perplexity"
    
    # Initialize defaults
    api_key = None
    model = None
    ollama_url = None
    
    if provider == "perplexity":
        api_key = get_api_key(session, "perplexity_api_key")
    elif provider == "groq":
        api_key = get_api_key(session, "groq_api_key")
        model = os.getenv("GROQ_MODEL")
        if not model:
            config_model = session.get(Config, "groq_model")
            model = get_secure_config().get_value(config_model) if config_model else "llama3-8b-8192"
    elif provider == "local":
        ollama_url = os.getenv("OLLAMA_URL")
        if not ollama_url:
            config_ollama = session.get(Config, "ollama_url")
            ollama_url = get_secure_config().get_value(config_ollama) if config_ollama else None

    return LLMService(
        api_key=api_key, 
        provider=provider, 
        model=model, 
        ollama_url=ollama_url
    )

class AnalysisEngine:
    """
    Core analysis engine for portfolio insights and performance tracking.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the analysis engine with a database session.
        """
        self.session = session

    def calculate_basket_performance(self) -> List[Dict[str, Any]]:
        """
        Calculate performance metrics for each investment theme/basket.
        """
        themes = self.session.exec(select(Theme)).all()
        results = []
        
        for theme in themes:
            total_invested = 0.0
            current_value = 0.0
            
            from backend.services.currency_service import CurrencyService
            usd_rate = CurrencyService().get_usd_inr_rate()
            
            for stock in theme.stocks:
                rate = usd_rate if stock.currency == "USD" else 1.0
                invested = stock.quantity * stock.average_price * rate
                curr = stock.quantity * stock.current_price * rate
                total_invested += invested
                current_value += curr
                
            if total_invested > 0:
                abs_return = current_value - total_invested
                pct_return = (abs_return / total_invested) * 100
            else:
                abs_return = 0.0
                pct_return = 0.0
                
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
        """
        stocks = self.session.exec(select(Stock)).all()
        
        stock_performance = []
        for stock in stocks:
            pct_change = stock.weekly_change_percentage if stock.weekly_change_percentage is not None else 0.0
            
            stock_performance.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "pct_change": pct_change,
                "current_price": stock.current_price
            })
            
        stock_performance.sort(key=lambda x: x["pct_change"], reverse=True)
        
        winners = stock_performance[:3]
        losers = stock_performance[-3:]
        
        from backend.services.scraper import NewsScraperService as Scraper
        scraper = Scraper()
        llm = get_llm_service(self.session)
        
        has_credentials = llm.api_key is not None or llm.provider == "local"

        async def _enrich_with_reason(item):
            if has_credentials:
                try:
                    news = await scraper.fetch_news(item["symbol"])
                    headlines = "\n".join([f"- {n.get('title')}" for n in news[:5]])

                    deep_data = await scraper.fetch_comprehensive_intelligence(item["symbol"], llm)
                    
                    deep_context = f"""
                    [HEADLINES]
                    {headlines}

                    [POLITICAL/GEO] {deep_data.get('political', 'N/A')}
                    [MACRO] {deep_data.get('macro', 'N/A')}
                    """
                except Exception as e:
                    logger.error(f"Deep Intel Error for {item['symbol']}: {e}")
                    deep_context = None

                res = await llm.analyze_stock_movement(item["symbol"], item["pct_change"], deep_context=deep_context)
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
        """
        stocks = self.session.exec(select(Stock)).all()
        llm = get_llm_service(self.session)
        has_credentials = llm.api_key is not None or llm.provider == "local"
        
        from backend.services.scraper import NewsScraperService as Scraper
        scraper = Scraper()
        
        for stock in stocks:
            pct_change = 0.0
            if stock.previous_close:
                 pct_change = ((stock.current_price - stock.previous_close) / stock.previous_close) * 100
            else:
                 pct_change = ((stock.current_price - stock.average_price) / stock.average_price) * 100
            
            if abs(pct_change) > 3.0:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                
                existing = self.session.exec(select(TimelineEvent).where(
                    TimelineEvent.related_stock_symbol == stock.symbol
                ).where(TimelineEvent.date >= today_start)).first()
                
                if not existing:
                    direction = "surged" if pct_change > 0 else "plunged"
                    description = f"{stock.name} saw significant movement."
                    citations_json = None
                    if has_credentials:
                        try:
                            news = await scraper.fetch_news(stock.symbol)
                            headlines = "\n".join([f"- {n.get('title')}" for n in news[:5]])
                            deep_data = await scraper.fetch_comprehensive_intelligence(stock.symbol, llm)
                            deep_context = f"""
                            [HEADLINES]
                            {headlines}
                            [POLITICAL/GEO] {deep_data.get('political', 'N/A')}
                            [MACRO] {deep_data.get('macro', 'N/A')}
                            """
                            
                            res = await llm.analyze_stock_movement(stock.symbol, pct_change, deep_context=deep_context)
                            description = res["reason"]
                            import json
                            if res["citations"]:
                                citations_json = json.dumps(res["citations"])
                        except Exception as e:
                            logger.error(f"Error generating LLM reason for {stock.symbol}: {e}")
                            pass
                    
                    event = TimelineEvent(
                        title=f"{stock.symbol} {direction} by {pct_change:.1f}%",
                        description=description,
                        impact_percent=pct_change,
                        related_stock_symbol=stock.symbol,
                        date=datetime.utcnow(),
                        references=citations_json
                    )
                    self.session.add(event)

        self.session.commit()

    async def refresh_news(self):
        """
        Fetch fresh news for all stocks in the portfolio.
        """
        from backend.services.scraper import NewsScraperService as Scraper
        from backend.models import NewsArticle
        
        logger.info("Starting News Refresh...")
        llm = get_llm_service(self.session)
        scraper = Scraper()
        stocks = self.session.exec(select(Stock)).all()
        
        articles_added = 0
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        seen_urls = set()

        for stock in stocks:
            try:
                news_items = await scraper.fetch_news(stock.symbol, llm_service=llm)
                
                stock_articles_count = 0
                for item in news_items:
                    url = item.get("url", "")
                    if not url or url == "#" or url in seen_urls:
                        continue
                        
                    pub_time = item.get("published_date") or datetime.utcnow()
                    if pub_time < cutoff_date:
                        continue

                    exists = self.session.exec(select(NewsArticle).where(NewsArticle.url == url)).first()
                    if not exists:
                        article = NewsArticle(
                            stock_id=stock.id,
                            title=item.get("title", "") or "No Title",
                            url=url,
                            source=item.get("source") or "Unknown",
                            published_date=pub_time,
                            summary=f"News related to {stock.symbol}",
                            sentiment=None,
                            processing_status="pending"
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
