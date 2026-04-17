"""
Data Models - SQLModel Database Schema

This module defines all database models for the Stock Dashboard application.
Uses SQLModel (Pydantic + SQLAlchemy) for type-safe ORM with automatic
validation and serialization.

Models:
    - Stock: Individual stock holdings from various platforms
    - Theme: Investment themes/categories (e.g., "Tech", "Growth")
    - StockTheme: Many-to-many relationship between stocks and themes
    - PortfolioSnapshot: Historical portfolio value tracking
    - TimelineEvent: Significant events in portfolio history
    - NewsArticle: Scraped news articles for stocks
    - Config: Application configuration and API keys
"""

from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
import json

# TYPE_CHECKING prevents circular import at runtime
if TYPE_CHECKING:
    from backend.models import StockTheme


class StockTheme(SQLModel, table=True):
    """
    Association table for many-to-many relationship between Stock and Theme.
    
    Allows a stock to belong to multiple themes (e.g., AAPL can be in both
    "Tech" and "Growth" themes), and a theme to contain multiple stocks.
    
    Attributes:
        stock_id: Foreign key to Stock table (composite primary key)
        theme_id: Foreign key to Theme table (composite primary key)
    """
    stock_id: Optional[int] = Field(default=None, foreign_key="stock.id", primary_key=True)
    theme_id: Optional[int] = Field(default=None, foreign_key="theme.id", primary_key=True)


class Theme(SQLModel, table=True):
    """
    Investment theme/category for organizing stocks.
    
    Themes (also called baskets) allow grouping stocks by strategy, sector,
    or any custom categorization. Examples: "Tech Giants", "Dividend Stocks",
    "ESG Portfolio".
    
    Attributes:
        id: Auto-increment primary key
        name: Unique theme name (indexed for fast lookup)
        description: Optional description of investment thesis
        stocks: Relationship to Stock model (many-to-many via StockTheme)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    
    # Bidirectional relationship with stocks
    stocks: List["Stock"] = Relationship(back_populates="themes", link_model=StockTheme)


class TimelineEvent(SQLModel, table=True):
    """
    Significant event in portfolio history.
    
    Tracks major price movements, news events, or user-defined milestones.
    Used to populate the portfolio timeline/activity feed.
    
    Attributes:
        id: Auto-increment primary key
        date: Event timestamp (defaults to current UTC time)
        title: Short event description (e.g., "TSLA surged by 7.2%")
        description: Detailed event explanation
        impact_percent: Price change percentage (threshold: typically >5% or <-5%)
        related_stock_symbol: Optional stock symbol if event is stock-specific
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(default_factory=datetime.utcnow, index=True)
    title: str
    description: str
    impact_percent: float  # Significant if > 5.0 or < -5.0
    related_stock_symbol: Optional[str] = None
    references: Optional[str] = None # JSON string of URLs


class Stock(SQLModel, table=True):
    """
    Individual stock holding from a brokerage platform.
    
    Represents a single stock position, including quantity, prices, and
    metadata. Supports multi-platform portfolios (Zerodha, Vested) and
    multi-currency holdings (INR, USD).
    
    Attributes:
        id: Auto-increment primary key
        symbol: Stock ticker symbol (e.g., "AAPL", "RELIANCE")
        name: Full company name
        quantity: Number of shares held
        average_price: Average purchase price per share
        current_price: Latest market price per share
        currency: Currency code ("INR" or "USD")
        platform: Brokerage platform ("zerodha" or "vested")
        asset_class: Type of asset ("EQUITY", "ETF", etc.)
        last_synced: Timestamp of last data sync from platform
        themes: Relationship to Theme model (many-to-many via StockTheme)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)  # Indexed for fast symbol-based queries
    name: str
    quantity: float
    average_price: float
    current_price: float
    currency: str = Field(default="INR")  # INR or USD
    platform: str  # "zerodha" or "vested"
    asset_class: str = Field(default="EQUITY")
    last_synced: datetime = Field(default_factory=datetime.utcnow)
    last_analyzed: Optional[datetime] = Field(default=None)
    
    # Bidirectional relationship with themes
    themes: List[Theme] = Relationship(back_populates="stocks", link_model=StockTheme)
    
    # New V9: Previous Close for Day Change Calc
    previous_close: Optional[float] = Field(default=None)
    weekly_change_percentage: Optional[float] = Field(default=None)


class PortfolioSnapshot(SQLModel, table=True):
    """
    Historical snapshot of total portfolio value.
    
    Captures portfolio value at a point in time for trend analysis and
    performance tracking. Used to generate portfolio value charts.
    
    Attributes:
        id: Auto-increment primary key
        timestamp: Snapshot datetime (defaults to current UTC time)
        total_value_inr: Total portfolio value in INR (multi-currency converted)
        day_change_inr: Daily change in value (INR)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_value_inr: float
    day_change_inr: Optional[float] = 0.0


class NewsArticle(SQLModel, table=True):
    """
    Scraped news article for a specific stock.
    
    Stores news articles fetched from various sources (Google News, RSS feeds)
    for stock-specific news display and sentiment analysis.
    
    Attributes:
        id: Auto-increment primary key
        stock_id: Foreign key to Stock table
        title: Article headline
        summary: Article summary/snippet (optional)
        source: News source (e.g., "Google News", "Economic Times")
        url: Full URL to article
        published_date: Article publication datetime (optional)
        scraped_at: Datetime when article was scraped (defaults to now)
        sentiment: Sentiment analysis result ("positive", "negative", "neutral")
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    stock_id: int = Field(foreign_key="stock.id")
    title: str
    summary: Optional[str] = None
    source: str  # e.g., "Economic Times", "MoneyControl"
    url: str
    published_date: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    sentiment: Optional[str] = None  # "positive", "negative", "neutral"
    credibility_score: int = Field(default=5)  # 1-10 score based on source
    processing_status: str = Field(default="pending", index=True)  # pending, processing, completed, failed


class Config(SQLModel, table=True):
    """
    Application configuration and API key storage.
    
    Key-value store for application settings, API credentials, and cached data.
    Sensitive values (API keys) are stored encrypted.
    
    Common keys:
        - perplexity_api_key: Perplexity AI API key (Encrypted)
        - groq_api_key: Groq API key (Encrypted)
        - zerodha_api_key: Zerodha Kite Connect API key (Encrypted)
        - zerodha_api_secret: Zerodha API secret (Encrypted)
        - zerodha_access_token: Zerodha OAuth access token (Encrypted)
        - theme_summary_{id}: Cached LLM theme summary
        - portfolio_summary: Cached LLM portfolio summary
    
    Attributes:
        key: Configuration key (primary key, unique)
        value: Configuration value (stored as string, JSON for complex data)
        is_encrypted: Flag indicating if the value is encrypted
        updated_at: Last update timestamp (defaults to current UTC time)
    """
    key: str = Field(primary_key=True)
    value: str
    is_encrypted: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Read Models for API Serialization
# These models are used for API responses and don't map to database tables

class ThemeRead(SQLModel):
    """
    API response model for Theme with calculated fields.
    
    Extends base Theme with computed values that aren't stored in database.
    Used for GET /api/themes endpoint.
    
    Attributes:
        id: Theme ID
        name: Theme name
        description: Theme description
        stock_count: Number of stocks in theme (calculated)
        total_value: Total value of all stocks in theme (calculated)
    """
    id: int
    name: str
    description: Optional[str] = None
    stock_count: int = 0  # Calculated field
    total_value: float = 0.0  # Calculated field


class StockRead(SQLModel):
    """
    API response model for Stock with themed information.
    
    Extends base Stock with theme relationship data for API responses.
    Used for GET /api/stocks endpoint.
    
    Attributes:
        All Stock attributes plus:
        themes: List of theme names this stock belongs to (calculated)
        day_change: Calculated price change
        day_change_percentage: Calculated % change
    """
    id: int
    symbol: str
    name: str
    quantity: float
    average_price: float
    current_price: float
    previous_close: Optional[float] = None
    currency: str
    platform: str
    asset_class: str
    last_synced: datetime
    themes: List[ThemeRead] = []  # List of ThemeRead objects
    day_change: float = 0.0
    weekly_change_percentage: Optional[float] = 0.0
