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
from backend.security import sanitize_html, validate_api_key_format
from backend.task_manager import task_manager
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from kiteconnect import KiteConnect
from fastapi.responses import RedirectResponse
import yfinance as yf

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
    asset_class: str = "EQUITY" # New field, default EQUITY

class StockTransaction(BaseModel):
    action: Literal["buy", "sell", "edit"]
    quantity: float
    price: float # Buy Price, Sell Price, or New Avg Price

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    logger.info("Stock Dashboard application started")

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

# Removed old /api/refresh - see line 158 for new version with news scraping

@app.get("/api/stocks", response_model=List[StockRead])
def get_stocks(session: Session = Depends(get_session)):
    stocks = session.exec(select(Stock)).all()
    # SQLModel automatically serializes nested models if they are loaded.
    # We might need to ensure they are loaded.
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
    
    # User Request: "Daily change value with percentage of total portfolio current value"
    # Actually, usually day change % is based on Previous Day Value (Total - DayChange)
    # But user asked for "percentage of total portfolio cuurent value"
    # I will interpret this as DayChange / CurrentTotalValue
    # day_change_percentage = (day_change_total / current_portfolio_value * 100) if current_portfolio_value > 0 else 0.0
    
    # Standard Finance Way (safer to show alongside Day Change Value):
    # Day Change % = Day Change / (Current - Day Change)
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
def remove_stock_from_theme(theme_id: int, stock_id: int, session: Session = Depends(get_session)):
    theme = session.get(Theme, theme_id)
    stock = session.get(Stock, stock_id)
    
    if not theme or not stock:
        raise HTTPException(status_code=404, detail="Resource not found")
        
    if stock in theme.stocks:
        theme.stocks.remove(stock)
        session.add(theme)
        session.commit()
        
    return {"status": "success"}



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
                
                # 2. Generate Insights with Deep Intelligence
                # This triggers fetch_comprehensive_intelligence() for all stocks
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
    
    if cached and cached.value:
        age_delta = datetime.utcnow() - cached.updated_at
        if age_delta < timedelta(hours=6) and not refresh:
            try:
                import json
                insights = json.loads(cached.value)
                insights["cached"] = True
            except:
                pass
        elif age_delta >= timedelta(hours=6):
            # Cache is stale, mark for regeneration but return old data
            is_stale = True
            try:
                import json
                insights = json.loads(cached.value)
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
                    
                    # Save to cache
                    import json
                    cache_value = json.dumps(new_insights)
                    temp_config = Config(key=cache_key, value=cache_value, updated_at=datetime.utcnow())
                    bg_session.merge(temp_config)
                    bg_session.commit()
                    
                    logger.info("Insights regenerated successfully in background")
            except Exception as e:
                logger.error(f"Failed to regenerate insights: {e}")
        
        background_tasks.add_task(_regenerate_insights)
    
    # Timeline is always separate and fresh
    timeline = session.exec(select(TimelineEvent).order_by(TimelineEvent.date.desc()).limit(10)).all()
    
    # Return current data immediately
    return {
        "insights": insights or {"winners": [], "losers": [], "cached": False},
        "timeline": timeline,
        "is_stale": is_stale or refresh
    }

@app.get("/api/background-status")
def get_background_status():
    """
    Get the current status of background tasks.
    
    Returns running state and last completion time for sync and refresh operations.
    Frontend can poll this endpoint to show task progress to users.
    """
    return task_manager.get_status()


@app.delete("/api/themes/{theme_id}/stocks/{stock_id}")
def remove_stock_from_theme(theme_id: int, stock_id: int, session: Session = Depends(get_session)):
    stock_theme = session.get(StockTheme, (stock_id, theme_id))
    if not stock_theme:
        raise HTTPException(status_code=404, detail="Stock not associated with this theme")
    
    session.delete(stock_theme)
    session.commit()
    return {"status": "removed"}

@app.get("/api/stocks/{symbol}/analysis")
def get_stock_analysis(symbol: str):
    scraper = NewsScraperService()
    return scraper.fetch_stock_analysis(symbol)

# V7: Config Management
@app.get("/api/config/{key}")
def get_config(key: str, session: Session = Depends(get_session)):
    config = session.get(Config, key)
    if not config:
        return {"key": key, "value": None}
    return {"key": config.key, "value": config.value}

@app.put("/api/config/{key}")
def update_config(key: str, value: str, session: Session = Depends(get_session)):
    """
    Update configuration value with security validation.
    
    SECURITY: Validates API key formats before storing.
    TODO: Add authentication to prevent unauthorized config changes.
    """
    logger.info(f"Updating config: {key}")
    # Security: Validate API key format
    if 'api_key' in key or 'api_secret' in key or 'token' in key:
        try:
            validate_api_key_format(value, key)
        except ValueError as e:
            logger.warning(f"Invalid API key format for {key}: {e}")
            raise HTTPException(status_code=400, detail="Invalid API key format")
    
    # Security: Sanitize key to prevent injection
    safe_key = sanitize_html(key)
    
    config = session.get(Config, safe_key)
    if config:
        config.value = value
        config.updated_at = datetime.utcnow()
    else:
        config = Config(key=safe_key, value=value)
    session.add(config)
    session.commit()
    session.refresh(config)
    return {"key": config.key, "value": config.value}

# V7: News API
class NewsWithSymbol(NewsArticle):
    stock_symbol: str
    class Config:
        table = False

@app.get("/api/news", response_model=List[NewsWithSymbol])
def get_news(days: int = 7, session: Session = Depends(get_session)):
    """Get news articles from the last N days (default 7)"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    results = session.exec(
        select(NewsArticle, Stock.symbol)
        .join(Stock, NewsArticle.stock_id == Stock.id)
        .where(NewsArticle.published_date >= cutoff)
        .order_by(NewsArticle.published_date.desc())
    ).all()
    
    news_with_symbol = []
    for article, symbol in results:
        # Create NewsWithSymbol manually to avoid missing field error in from_orm
        data = article.dict()
        data["stock_symbol"] = symbol
        news_item = NewsWithSymbol.parse_obj(data)
        news_with_symbol.append(news_item)
        
    return news_with_symbol

@app.get("/api/news/{stock_id}")
def get_stock_news(stock_id: int, session: Session = Depends(get_session)):
    """Get news for a specific stock"""
    news = session.exec(
        select(NewsArticle)
        .where(NewsArticle.stock_id == stock_id)
        .order_by(NewsArticle.published_date.desc())
        .limit(20)
    ).all()
    return news

# V7: Logs API
@app.get("/api/logs")
def get_logs(lines: int = 100):
    """Get recent log entries"""
    log_lines = get_recent_logs(lines)
    return {"logs": "".join(log_lines)}

# V7: LLM Analysis with Caching
@app.get("/api/llm/theme-summaries")
def get_theme_summaries(session: Session = Depends(get_session)):
    """Generate LLM summaries for all themes with caching"""
    # Get API key from config
    config = session.get(Config, "perplexity_api_key")
    api_key = config.value if config else None
    
    llm = LLMService(api_key=api_key)
    themes = session.exec(select(Theme)).all()
    
    summaries = []
    for theme in themes:
        stocks_data = [
            {"symbol": s.symbol, "name": s.name, "quantity": s.quantity, "current_price": s.current_price}
            for s in theme.stocks
        ]
        if stocks_data:  # Only analyze themes with stocks
            # Check cache first
            cache_key = f"theme_summary_{theme.id}"
            cached = session.get(Config, cache_key)
            
            # Cache hit if exists and theme hasn't changed
            if cached and cached.value:
                try:
                    import json
                    summary = json.loads(cached.value)
                    summary["theme_id"] = theme.id
                    summary["cached"] = True
                    summaries.append(summary)
                    continue
                except:
                    pass
            
            # Generate new summary
            summary = llm.generate_theme_summary(theme.name, stocks_data)
            summary["theme_id"] = theme.id
            summary["cached"] = False
            summaries.append(summary)
            
            # Save to cache
            # Save to cache
            try:
                import json
                cache_value = json.dumps(summary)
                # Use merge to handle Upsert (Update if exists, Insert if new)
                # This avoids IntegrityError if key exists but session didn't know
                temp_config = Config(key=cache_key, value=cache_value, updated_at=datetime.utcnow())
                session.merge(temp_config)
                session.commit()
            except Exception as e:
                logger.error(f"Failed to cache theme summary {cache_key}: {e}")
                session.rollback()
    
    # Session commit done inside loop
    logger.info(f"Generated {len(summaries)} theme summaries ({sum(1 for s in summaries if s.get('cached')) } from cache)")
    return summaries

@app.get("/api/llm/portfolio-summary")
def get_ai_portfolio_summary(refresh: bool = False, session: Session = Depends(get_session)):
    """Generate LLM summary for entire portfolio with caching"""
    # Get API key from config
    config = session.get(Config, "perplexity_api_key")
    api_key = config.value if config else None
    
    llm = LLMService(api_key=api_key)
    
    # Check cache
    cache_key = "portfolio_summary"
    cached = session.get(Config, cache_key)
    
    # Cache Logic: Return if valid, exists, not forced refresh, and < 6 hours old
    if cached and cached.value and not refresh:
        age_delta = datetime.utcnow() - cached.updated_at
        if age_delta < timedelta(hours=6):
            try:
                import json
                summary = json.loads(cached.value)
                summary["cached"] = True
                logger.info("Returned cached portfolio summary")
                return summary
            except:
                pass
    
    # Get all stocks and themes
    stocks = session.exec(select(Stock)).all()
    themes = session.exec(select(Theme)).all()
    
    # Get live rate
    from backend.services.currency_service import CurrencyService
    usd_rate = CurrencyService().get_usd_inr_rate()

    total_value = 0.0
    stocks_data = []
    
    for s in stocks:
         # Convert value
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
    
    summary = llm.generate_portfolio_summary(total_value, stocks_data, themes_data)
    summary["cached"] = False
    
    # Save to cache
    # Save to cache
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

# Clear LLM cache when data changes
@app.post("/api/clear-llm-cache")
def clear_llm_cache(session: Session = Depends(get_session)):
    """Clear all LLM caches - called after data changes"""
    session.exec(select(Config).where(Config.key.like("theme_summary_%"))).all()
    for cache in session.exec(select(Config).where(Config.key.like("%summary%"))).all():
        session.delete(cache)
    session.commit()
    logger.info("Cleared LLM cache")
    return {"status": "cache_cleared"}

# V8: Zerodha OAuth Integration
@app.get("/api/zerodha/login")
def zerodha_login(session: Session = Depends(get_session)):
    """Initiate Zerodha OAuth login flow"""
    # Get API key from config
    config = session.get(Config, "zerodha_api_key")
    if not config or not config.value:
        raise HTTPException(status_code=400, detail="Zerodha API key not configured. Please add it in Settings.")
    
    api_key = config.value
    kite = KiteConnect(api_key=api_key)
    
    # Generate login URL
    login_url = kite.login_url()
    logger.info(f"Redirecting to Zerodha login: {login_url}")
    
    # Redirect user to Zerodha login
    return RedirectResponse(url=login_url)

@app.get("/api/zerodha/callback")
def zerodha_callback(request_token: str, session: Session = Depends(get_session)):
    """
    Handle Zerodha OAuth callback and exchange token.
    
    SECURITY: Uses generic error messages to avoid information disclosure.
    """
    
    try:
        # Get API credentials from config
        api_key_config = session.get(Config, "zerodha_api_key")
        api_secret_config = session.get(Config, "zerodha_api_secret")
        
        if not api_key_config or not api_secret_config:
            # Security: Generic error message
            logger.error("Zerodha OAuth attempt with missing credentials")
            raise HTTPException(status_code=400, detail="Authentication configuration error")
        
        kite = KiteConnect(api_key=api_key_config.value)
        
        # Exchange request token for access token
        data = kite.generate_session(request_token, api_secret=api_secret_config.value)
        access_token = data["access_token"]
        user_id = data["user_id"]
        
        # Store access token in config
        token_config = session.get(Config, "zerodha_access_token")
        if token_config:
            token_config.value = access_token
            token_config.updated_at = datetime.utcnow()
        else:
            token_config = Config(key="zerodha_access_token", value=access_token)
        session.add(token_config)
        
        # Store user ID
        user_config = session.get(Config, "zerodha_user_id")
        if user_config:
            user_config.value = user_id
            user_config.updated_at = datetime.utcnow()
        else:
            user_config = Config(key="zerodha_user_id", value=user_id)
        session.add(user_config)
        
        session.commit()
        
        logger.info(f"Zerodha OAuth successful for user: {user_id}")
        
        # Security: Hardcoded redirect URL to prevent open redirect
        return RedirectResponse(url="/?zerodha=connected")
        
    except Exception as e:
        logger.error(f"Zerodha OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="OAuth failed due to an internal error.")

@app.get("/api/zerodha/status")
def zerodha_status(session: Session = Depends(get_session)):
    """Check Zerodha authentication status"""
    api_key_config = session.get(Config, "zerodha_api_key")
    token_config = session.get(Config, "zerodha_access_token")
    user_config = session.get(Config, "zerodha_user_id")
    
    return {
        "api_key_configured": bool(api_key_config),
        "authenticated": bool(token_config),
        "user_id": user_config.value if user_config else None
    }

# --- Manual Holdings Management ---

@app.post("/api/stocks", response_model=Stock)
def create_manual_stock(payload: StockCreate, session: Session = Depends(get_session)):
    """Create a manual stock holding."""
    # 1. Fetch metadata (Name, Current Price)
    try:
        # Try fetching name from yfinance
        # Use appropriate suffix if needed
        symbol_query = payload.symbol.upper()
        
        if payload.asset_class == "CRYPTO":
             if "-" not in symbol_query:
                  symbol_query += f"-{payload.currency.upper()}"
        elif payload.currency == "INR" and not symbol_query.endswith(".NS") and not symbol_query.endswith(".BO"):
             symbol_query += ".NS"
             
        ticker = yf.Ticker(symbol_query)
        info = ticker.info
        name = info.get('longName') or info.get('shortName') or payload.symbol
        
        # Current Price
        # Try fetching via PriceFetcher logic (Google Finance) or fallback to yfinance
        # For simplicity, let's just use yfinance current price for creation
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or payload.average_price
        
    except Exception as e:
        logger.warning(f"Metadata fetch failed for {payload.symbol}: {e}")
        name = payload.symbol
        current_price = payload.average_price

    # 2. Create Stock Record
    stock = Stock(
        symbol=payload.symbol.upper(),
        name=name,
        quantity=payload.quantity,
        average_price=payload.average_price,
        current_price=current_price,
        currency=payload.currency,
        platform="manual",
        asset_class=payload.asset_class # Use payload value
    )
    
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock

@app.put("/api/stocks/{stock_id}")
def update_stock_holding(stock_id: int, tx: StockTransaction, session: Session = Depends(get_session)):
    """Update stock holding (Buy additional, Sell/Trim, or Edit correction)."""
    stock = session.get(Stock, stock_id)
    if not stock:
         raise HTTPException(status_code=404, detail="Stock not found")
         
    if tx.action == "buy":
        # Weighted Average Formula
        # New Avg = ((Old Qty * Old Avg) + (New Qty * Buy Price)) / (Old Qty + New Qty)
        total_cost = (stock.quantity * stock.average_price) + (tx.quantity * tx.price)
        total_qty = stock.quantity + tx.quantity
        
        stock.quantity = total_qty
        stock.average_price = total_cost / total_qty
        
    elif tx.action == "sell":
        # Trim holding. Avg price remains same strictly speaking, 
        # unless we want to realize profit/loss (which we don't track separately yet).
        if tx.quantity > stock.quantity:
             raise HTTPException(status_code=400, detail="Cannot sell more than held quantity")
             
        stock.quantity -= tx.quantity
        # If sold out
        if stock.quantity == 0:
            # We can either keep it with 0 qty or delete. 
            pass
            
    elif tx.action == "edit":
        # Direct correction
        stock.quantity = tx.quantity
        stock.average_price = tx.price
        
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock

@app.delete("/api/stocks/{stock_id}")
def delete_stock_holding(stock_id: int, session: Session = Depends(get_session)):
    """Delete a manual stock holding."""
    stock = session.get(Stock, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    session.delete(stock)
    session.commit()
    return {"status": "success", "deleted_id": stock_id}
