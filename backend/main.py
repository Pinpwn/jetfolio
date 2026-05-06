"""  
Stock Dashboard API - Main Application

This is the main FastAPI application providing portfolio management,
broker integration, and AI-powered insights.

SECURITY NOTES:
    - Authentication required for production deployment
    - HTTPS/TLS required for credential transmission
    - See SECURITY_ASSESSMENT.md for complete security audit
    - Encryption key required: set ENCRYPTION_KEY environment variable
"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlmodel import Session, select
from typing import List, Optional, Literal
from backend.services.price_fetcher import PriceFetcher
from backend.services.scraper import NewsScraperService

from backend.database import create_db_and_tables, get_session
from backend.models import Stock, PortfolioSnapshot, Theme, StockTheme, TimelineEvent, StockRead, ThemeRead, NewsArticle, Config
from backend.sync_engine import SyncEngine
from backend.analysis_engine import AnalysisEngine
from backend.logger import logger, get_recent_logs
from backend.llm_service import LLMService
from backend.middleware import SecurityHeadersMiddleware
from backend.security import sanitize_html, validate_api_key_format, get_secure_config, get_api_key
from backend.task_manager import task_manager
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from kiteconnect import KiteConnect
from fastapi.responses import RedirectResponse
import yfinance as yf
import httpx

app = FastAPI(
    title="Stock Dashboard API",
    description="Multi-platform portfolio management with AI insights",
    version="1.0.0"
)

# Security: Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class ThemeCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class StockAssign(BaseModel):
    stock_ids: List[int]

class StockCreate(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    currency: str = "INR"
    asset_class: str = "EQUITY"

class StockTransaction(BaseModel):
    action: Literal["buy", "sell", "edit"]
    quantity: float
    price: float # Buy Price, Sell Price, or New Avg Price

@app.on_event("startup")
def on_startup():
    """Application startup initialization. Sets up database and performs schema migrations."""
    create_db_and_tables()
    logger.info("Stock Dashboard application started")

def get_llm_service(session: Session) -> LLMService:
    """
    Helper to initialize LLMService with configured provider and credentials.
    Priority: Environment Variables > Encrypted Database Config.
    """
    import os
    
    # 1. Determine Provider
    # Priority: LLM_PROVIDER env var > llm_provider db config
    provider = os.getenv("LLM_PROVIDER")
    if not provider:
        config_provider = session.get(Config, "llm_provider")
        provider = config_provider.value if config_provider else "perplexity"
    
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

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/sync")
def sync_data(background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """Trigger data sync from all connected platforms + Fetch News"""
    # Return current data immediately, run sync in background
    async def _run_sync():
        """Background task for data synchronization"""
        task_manager.start_sync()
        try:
            # Create new session for background task
            from backend.database import engine
            with Session(engine) as bg_session:
                sync_engine = SyncEngine()
                await sync_engine.run_sync()
                
                # Analyze (Generate Timeline, etc)
                analysis_engine = AnalysisEngine(bg_session)
                await analysis_engine.detect_significant_events()
                
                logger.info("Background sync completed successfully")
        except Exception as e:
            logger.error(f"Background sync failed: {e}")
        finally:
            task_manager.complete_sync()
    
    # Schedule background task
    background_tasks.add_task(_run_sync)
    
    # Return current portfolio data immediately
    stocks = session.exec(select(Stock)).all()
    snapshot = session.exec(select(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)).first()
    
    return {
        "status": "sync_started",
        "message": "Data sync running in background. Current data returned.",
        "stock_count": len(stocks),
        "last_snapshot_time": snapshot.timestamp.isoformat() if snapshot else None
    }

@app.get("/api/stocks", response_model=List[StockRead])
def get_stocks(session: Session = Depends(get_session)):
    stocks = session.exec(select(Stock)).all()
    return stocks

@app.get("/api/portfolio")
def get_portfolio_summary(session: Session = Depends(get_session)):
    # Get latest snapshot
    snapshot = session.exec(select(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)).first()
    
    analysis_engine = AnalysisEngine(session)
    basket_performance = analysis_engine.calculate_basket_performance()
    
    # Get allocation by asset class
    stocks = session.exec(select(Stock)).all()
    allocation = {}
    
    current_portfolio_value = 0.0
    day_change_total = 0.0
    invested_value_inr = 0.0
    
    for stock in stocks:
        val = stock.quantity * stock.current_price
        invested = stock.quantity * stock.average_price
        
        # Calculate Day Change
        change = 0.0
        if stock.previous_close and stock.previous_close > 0:
            change = (stock.current_price - stock.previous_close) * stock.quantity
        
        # Normalize to INR for pie chart
        if stock.currency == "USD":
            from backend.services.currency_service import CurrencyService
            rate = CurrencyService().get_usd_inr_rate()
            val *= rate
            change *= rate
            invested *= rate
            
        current_portfolio_value += val
        day_change_total += change
        invested_value_inr += invested
            
        ac = stock.asset_class
        allocation[ac] = allocation.get(ac, 0) + val
        
    # Calculate Percentages
    overall_growth_inr = current_portfolio_value - invested_value_inr
    overall_growth_percentage = (overall_growth_inr / invested_value_inr * 100) if invested_value_inr > 0 else 0.0
    
    prev_total_value = current_portfolio_value - day_change_total
    day_change_percentage = (day_change_total / prev_total_value * 100) if prev_total_value > 0 else 0.0
    
    return {
        "total_value_inr": current_portfolio_value,
        "invested_value_inr": invested_value_inr,
        "overall_growth_inr": overall_growth_inr,
        "overall_growth_percentage": overall_growth_percentage,
        "day_change_inr": day_change_total,
        "day_change_percentage": day_change_percentage,
        "allocation": allocation,
        "basket_performance": basket_performance
    }

@app.get("/api/themes", response_model=List[ThemeRead])
def get_themes(session: Session = Depends(get_session)):
    themes = session.exec(select(Theme)).all()
    # Calculate count and value manually
    from backend.services.currency_service import CurrencyService
    usd_rate = CurrencyService().get_usd_inr_rate()
    
    res = []
    for t in themes:
        val = 0.0
        for s in t.stocks:
            rate = usd_rate if s.currency == "USD" else 1.0
            val += s.quantity * s.current_price * rate
            
        tr = ThemeRead(
            id=t.id, 
            name=t.name, 
            description=t.description, 
            stock_count=len(t.stocks),
            total_value=val
        )
        res.append(tr)
    return res

@app.post("/api/themes", response_model=Theme)
def create_theme(theme: ThemeCreate, session: Session = Depends(get_session)):
    db_theme = Theme(name=theme.name, description=theme.description)
    session.add(db_theme)
    session.commit()
    session.refresh(db_theme)
    return db_theme

@app.put("/api/themes/{theme_id}")
def update_theme(theme_id: int, theme_data: ThemeUpdate, session: Session = Depends(get_session)):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
        
    if theme_data.name:
        theme.name = theme_data.name
    if theme_data.description:
        theme.description = theme_data.description
        
    session.add(theme)
    session.commit()
    session.refresh(theme)
    return theme

@app.post("/api/themes/{theme_id}/stocks")
def add_stocks_to_theme(theme_id: int, payload: StockAssign, session: Session = Depends(get_session)):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
        
    for stock_id in payload.stock_ids:
        stock = session.get(Stock, stock_id)
        if stock and stock not in theme.stocks:
            theme.stocks.append(stock)
            
    session.add(theme)
    session.commit()
    return {"status": "success", "added_count": len(payload.stock_ids)}

@app.delete("/api/themes/{theme_id}/stocks/{stock_id}")
def remove_stock_from_theme_api(theme_id: int, stock_id: int, session: Session = Depends(get_session)):
    stock_theme = session.get(StockTheme, (stock_id, theme_id))
    if not stock_theme:
        raise HTTPException(status_code=404, detail="Stock not associated with this theme")
    
    session.delete(stock_theme)
    session.commit()
    return {"status": "removed"}

@app.post("/api/refresh")
def refresh_insights(background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """Refresh insights AND scrape news for all stocks"""
    logger.info("Starting refresh insights + news scraping")
    
    async def _run_refresh():
        """Background task for news refresh, event detection, and deep intelligence"""
        task_manager.start_refresh()
        try:
            from backend.database import engine
            with Session(engine) as bg_session:
                analysis_engine = AnalysisEngine(bg_session)
                
                # 1. Fetch News First (so analysis can use it)
                await analysis_engine.refresh_news()
                
                # 1.5. Trigger Background Analysis for new articles
                from backend.services.analysis_manager import AnalysisManager
                logger.info("Triggering background analysis for pending articles...")
                AnalysisManager().process_pending_articles_background()
                
                # 2. Generate Insights with Deep Intelligence
                logger.info("Generating insights with Deep Intelligence...")
                new_insights = await analysis_engine.generate_insights()
                
                # 3. Save insights to cache
                import json
                cache_key = "weekly_insights_cache"
                cache_value = json.dumps(new_insights)
                temp_config = Config(key=cache_key, value=cache_value, updated_at=datetime.utcnow())
                bg_session.merge(temp_config)
                bg_session.commit()
                logger.info("Insights with Deep Intelligence cached successfully")
                
                # 4. Run Event Detection
                await analysis_engine.detect_significant_events()
                
                # Clear LLM cache so summaries regenerate with new data
                for cache in bg_session.exec(select(Config).where(Config.key.like("%summary%"))).all():
                    bg_session.delete(cache)
                bg_session.commit()
                
                logger.info("Background refresh completed successfully")
        except Exception as e:
            logger.error(f"Background refresh failed: {e}")
        finally:
            task_manager.complete_refresh()
    
    # Schedule background task
    background_tasks.add_task(_run_refresh)
    
    return {"status": "refresh_started", "message": "News refresh running in background"}

@app.get("/api/insights")
def get_insights(refresh: bool = False, background_tasks: BackgroundTasks = None, session: Session = Depends(get_session)):
    
    # 1. Check Cache for Insights (Winners/Losers) - 6h expiry
    cache_key = "weekly_insights_cache"
    cached = session.get(Config, cache_key)
    insights = None
    is_stale = False
    
    if cached and get_secure_config().get_value(cached):
        age_delta = datetime.utcnow() - cached.updated_at
        if age_delta < timedelta(hours=6) and not refresh:
            try:
                import json
                insights = json.loads(get_secure_config().get_value(cached))
                insights["cached"] = True
            except:
                pass
        elif age_delta >= timedelta(hours=6):
            is_stale = True
            try:
                import json
                insights = json.loads(get_secure_config().get_value(cached))
                insights["cached"] = True
            except:
                pass
                
    # 2. If refresh requested or stale, regenerate in background
    if (refresh or is_stale) and background_tasks:
        async def _regenerate_insights():
            """Background task to regenerate insights"""
            try:
                from backend.database import engine
                with Session(engine) as bg_session:
                    analysis_engine = AnalysisEngine(bg_session)
                    new_insights = await analysis_engine.generate_insights()
                    new_insights["cached"] = False
                    
                    import json
                    cache_value = json.dumps(new_insights)
                    temp_config = Config(key=cache_key, value=cache_value, updated_at=datetime.utcnow())
                    bg_session.merge(temp_config)
                    bg_session.commit()
                    
                    logger.info("Insights regenerated successfully in background")
            except Exception as e:
                logger.error(f"Failed to regenerate insights: {e}")
        
        background_tasks.add_task(_regenerate_insights)
    
    timeline = session.exec(select(TimelineEvent).order_by(TimelineEvent.date.desc()).limit(10)).all()
    
    return {
        "insights": insights or {"winners": [], "losers": [], "cached": False},
        "timeline": timeline,
        "is_stale": is_stale or refresh
    }

@app.get("/api/background-status")
def get_background_status():
    return task_manager.get_status()

@app.get("/api/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    scraper = NewsScraperService()
    llm = get_llm_service(session)
    analysis_data = await scraper.fetch_stock_analysis(symbol, llm_service=llm)
    
    # Persist News to DB
    stock = session.exec(select(Stock).where(Stock.symbol == symbol)).first()
    if stock and "latest_news" in analysis_data:
        for item in analysis_data["latest_news"]:
             url = item.get("url", "#")
             exists = session.exec(select(NewsArticle).where(NewsArticle.url == url)).first()
             if not exists:
                 article = NewsArticle(
                     stock_id=stock.id,
                     title=item.get("title", "No Title"),
                     url=url,
                     source=item.get("source", "Unknown"),
                     published_date=datetime.utcnow(),
                     processing_status="pending"
                 )
                 session.add(article)
        session.commit()
    
    from backend.services.analysis_manager import AnalysisManager
    manager = AnalysisManager()
    background_tasks.add_task(manager.process_pending_articles_background)

    return analysis_data

@app.get("/api/config/{key}")
def get_config(key: str, session: Session = Depends(get_session)):
    """Retrieve configuration value. Masks sensitive values for security."""
    config = session.get(Config, key)
    if not config:
        return {"key": key, "value": None, "is_encrypted": False}
    
    real_value = get_secure_config().get_value(config)
    display_value = real_value
    is_sensitive = any(k in key.lower() for k in ["api_key", "api_secret", "token"])
    
    if config.is_encrypted or is_sensitive:
        if real_value and len(real_value) > 8:
            display_value = f"{real_value[:2]}...{real_value[-2:]} (Encrypted)"
        else:
            display_value = "******** (Encrypted)"
            
    return {"key": config.key, "value": display_value, "is_encrypted": config.is_encrypted}

@app.put("/api/config/{key}")
def update_config(key: str, value: str, session: Session = Depends(get_session)):
    """Update configuration value with security validation and encryption."""
    logger.info(f"Updating config: {key}")
    
    is_sensitive = any(k in key.lower() for k in ["api_key", "api_secret", "token"])
    if is_sensitive:
        try:
            validate_api_key_format(value, key)
        except ValueError as e:
            logger.warning(f"Invalid API key format for {key}: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    safe_key = sanitize_html(key)
    
    final_value = value
    is_encrypted = False
    if is_sensitive:
        try:
            secure_mgr = get_secure_config()
            final_value = secure_mgr.encrypt(value)
            is_encrypted = True
            logger.info(f"Encrypted sensitive config: {safe_key}")
        except Exception as e:
            logger.error(f"Encryption failed for {safe_key}: {e}")
            raise HTTPException(status_code=500, detail="Security encryption failed. Key not saved.")
    
    config = session.get(Config, safe_key)
    if config:
        config.value = final_value
        config.is_encrypted = is_encrypted
        config.updated_at = datetime.utcnow()
    else:
        config = Config(key=safe_key, value=final_value, is_encrypted=is_encrypted)
        
    session.add(config)
    session.commit()
    session.refresh(config)
    
    display_value = "******** (Saved Encrypted)" if is_encrypted else final_value
    return {"key": config.key, "value": display_value, "is_encrypted": config.is_encrypted}

class NewsWithSymbol(NewsArticle):
    stock_symbol: str
    class Config:
        table = False

@app.get("/api/news", response_model=List[NewsWithSymbol])
def get_news(days: int = 7, session: Session = Depends(get_session)):
    cutoff = datetime.utcnow() - timedelta(days=days)
    results = session.exec(
        select(NewsArticle, Stock.symbol)
        .join(Stock, NewsArticle.stock_id == Stock.id)
        .where(NewsArticle.published_date >= cutoff)
        .order_by(NewsArticle.published_date.desc())
    ).all()
    
    news_with_symbol = []
    for article, symbol in results:
        data = article.dict()
        data["stock_symbol"] = symbol
        news_item = NewsWithSymbol.parse_obj(data)
        news_with_symbol.append(news_item)
        
    return news_with_symbol

@app.get("/api/news/{stock_id}")
def get_stock_news(stock_id: int, session: Session = Depends(get_session)):
    news = session.exec(
        select(NewsArticle)
        .where(NewsArticle.stock_id == stock_id)
        .order_by(NewsArticle.published_date.desc())
        .limit(20)
    ).all()
    return news

@app.get("/api/logs")
def get_logs(lines: int = 100):
    log_lines = get_recent_logs(lines)
    return {"logs": "".join(log_lines)}

@app.get("/api/llm/theme-summaries")
async def get_theme_summaries(session: Session = Depends(get_session)):
    """Generate LLM summaries for all themes with caching"""
    llm = get_llm_service(session)
    themes = session.exec(select(Theme)).all()
    
    summaries = []
    for theme in themes:
        stocks_data = [
            {"symbol": s.symbol, "name": s.name, "quantity": s.quantity, "current_price": s.current_price}
            for s in theme.stocks
        ]
        if stocks_data:
            cache_key = f"theme_summary_{theme.id}"
            cached = session.get(Config, cache_key)
            
            if cached and get_secure_config().get_value(cached):
                try:
                    import json
                    summary = json.loads(get_secure_config().get_value(cached))
                    summary["theme_id"] = theme.id
                    summary["cached"] = True
                    summaries.append(summary)
                    continue
                except:
                    pass
            
            summary = await llm.generate_theme_summary(theme.name, stocks_data)
            summary["theme_id"] = theme.id
            summary["cached"] = False
            summaries.append(summary)
            
            try:
                import json
                cache_value = json.dumps(summary)
                temp_config = Config(key=cache_key, value=cache_value, updated_at=datetime.utcnow())
                session.merge(temp_config)
                session.commit()
            except Exception as e:
                logger.error(f"Failed to cache theme summary {cache_key}: {e}")
                session.rollback()
    
    logger.info(f"Generated {len(summaries)} theme summaries ({sum(1 for s in summaries if s.get('cached')) } from cache)")
    return summaries

@app.get("/api/ai/models/{provider}")
async def get_available_models(provider: str, session: Session = Depends(get_session)):
    config_key = session.get(Config, f"{provider}_api_key")
    api_key = get_secure_config().get_value(config_key) if config_key else None

    if not api_key:
         raise HTTPException(status_code=400, detail=f"API Key for {provider} not configured")

    llm = LLMService(api_key=api_key, provider=provider)
    models = await llm.get_available_models()
    return {"models": models}

@app.get("/api/llm/portfolio-summary")
async def get_ai_portfolio_summary(refresh: bool = False, session: Session = Depends(get_session)):
    """Generate LLM summary for entire portfolio with caching"""
    llm = get_llm_service(session)
    
    cache_key = "portfolio_summary"
    cached = session.get(Config, cache_key)
    
    if cached and get_secure_config().get_value(cached) and not refresh:
        age_delta = datetime.utcnow() - cached.updated_at
        if age_delta < timedelta(hours=6):
            try:
                import json
                summary = json.loads(get_secure_config().get_value(cached))
                summary["cached"] = True
                logger.info("Returned cached portfolio summary")
                return summary
            except:
                pass
    
    stocks = session.exec(select(Stock)).all()
    themes = session.exec(select(Theme)).all()
    
    from backend.services.currency_service import CurrencyService
    usd_rate = CurrencyService().get_usd_inr_rate()

    total_value = 0.0
    stocks_data = []
    
    for s in stocks:
         rate = usd_rate if s.currency == "USD" else 1.0
         val = s.quantity * s.current_price * rate
         total_value += val
         
         stocks_data.append({
             "symbol": s.symbol, 
             "name": s.name, 
             "value": val
         })
    
    themes_data = [
        {"name": t.name, "stock_count": len(t.stocks)}
        for t in themes
    ]
    
    summary = await llm.generate_portfolio_summary(total_value, stocks_data, themes_data)
    summary["cached"] = False
    
    try:
        import json
        cache_value = json.dumps(summary)
        temp_config = Config(key=cache_key, value=cache_value, updated_at=datetime.utcnow())
        session.merge(temp_config)
        session.commit()
    except Exception as e:
        logger.error(f"Failed to cache portfolio summary: {e}")
        session.rollback()
    
    logger.info("Generated new portfolio summary")
    return summary

@app.post("/api/clear-llm-cache")
def clear_llm_cache(session: Session = Depends(get_session)):
    for cache in session.exec(select(Config).where(Config.key.like("%summary%"))).all():
        session.delete(cache)
    session.commit()
    logger.info("Cleared LLM cache")
    return {"status": "cache_cleared"}

@app.get("/api/zerodha/login")
def zerodha_login(session: Session = Depends(get_session)):
    config = session.get(Config, "zerodha_api_key")
    api_key = get_secure_config().get_value(config) if config else None
    
    if not api_key:
        raise HTTPException(status_code=400, detail="Zerodha API key not configured. Please add it in Settings.")
    
    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()
    logger.info(f"Redirecting to Zerodha login: {login_url}")
    return RedirectResponse(url=login_url)

@app.get("/api/zerodha/callback")
def zerodha_callback(request_token: str, session: Session = Depends(get_session)):
    try:
        api_key_config = session.get(Config, "zerodha_api_key")
        api_secret_config = session.get(Config, "zerodha_api_secret")
        
        api_key = get_secure_config().get_value(api_key_config) if api_key_config else None
        api_secret = get_secure_config().get_value(api_secret_config) if api_secret_config else None
        
        if not api_key or not api_secret:
            logger.error("Zerodha OAuth attempt with missing credentials")
            raise HTTPException(status_code=400, detail="Authentication configuration error")
        
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        user_id = data["user_id"]
        
        # Store access token and user ID - encrypted
        secure_mgr = get_secure_config()
        
        for key, val in [("zerodha_access_token", access_token), ("zerodha_user_id", user_id)]:
            config = session.get(Config, key)
            enc_val = secure_mgr.encrypt(val)
            if config:
                config.value = enc_val
                config.is_encrypted = True
                config.updated_at = datetime.utcnow()
            else:
                config = Config(key=key, value=enc_val, is_encrypted=True)
            session.add(config)
        
        session.commit()
        logger.info(f"Zerodha OAuth successful for user: {user_id}")
        return RedirectResponse(url="/?zerodha=connected")
        
    except Exception as e:
        logger.error(f"Zerodha OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="OAuth failed due to an internal error.")

@app.get("/api/zerodha/status")
def zerodha_status_endpoint(session: Session = Depends(get_session)):
    api_key_config = session.get(Config, "zerodha_api_key")
    token_config = session.get(Config, "zerodha_access_token")
    user_config = session.get(Config, "zerodha_user_id")
    
    return {
        "api_key_configured": bool(api_key_config),
        "authenticated": bool(token_config),
        "user_id": get_secure_config().get_value(user_config) if user_config else None
    }

@app.post("/api/stocks", response_model=Stock)
def create_manual_stock(payload: StockCreate, session: Session = Depends(get_session)):
    try:
        symbol_query = payload.symbol.upper()
        if payload.asset_class == "CRYPTO":
             if "-" not in symbol_query:
                  symbol_query += f"-{payload.currency.upper()}"
        elif payload.currency == "INR" and not symbol_query.endswith(".NS") and not symbol_query.endswith(".BO"):
             symbol_query += ".NS"
             
        ticker = yf.Ticker(symbol_query)
        info = ticker.info
        name = info.get('longName') or info.get('shortName') or payload.symbol
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or payload.average_price
        
    except Exception as e:
        logger.warning(f"Metadata fetch failed for {payload.symbol}: {e}")
        name = payload.symbol
        current_price = payload.average_price

    stock = Stock(
        symbol=payload.symbol.upper(),
        name=name,
        quantity=payload.quantity,
        average_price=payload.average_price,
        current_price=current_price,
        currency=payload.currency,
        platform="manual",
        asset_class=payload.asset_class
    )
    
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock

@app.put("/api/stocks/{stock_id}")
def update_stock_holding_endpoint(stock_id: int, tx: StockTransaction, session: Session = Depends(get_session)):
    stock = session.get(Stock, stock_id)
    if not stock:
         raise HTTPException(status_code=404, detail="Stock not found")
         
    if tx.action == "buy":
        total_cost = (stock.quantity * stock.average_price) + (tx.quantity * tx.price)
        total_qty = stock.quantity + tx.quantity
        stock.quantity = total_qty
        stock.average_price = total_cost / total_qty
    elif tx.action == "sell":
        if tx.quantity > stock.quantity:
             raise HTTPException(status_code=400, detail="Cannot sell more than held quantity")
        stock.quantity -= tx.quantity
    elif tx.action == "edit":
        stock.quantity = tx.quantity
        stock.average_price = tx.price
        
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock

@app.delete("/api/stocks/{stock_id}")
def delete_stock_holding_endpoint(stock_id: int, session: Session = Depends(get_session)):
    stock = session.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    session.delete(stock)
    session.commit()
    return {"status": "success", "deleted_id": stock_id}
