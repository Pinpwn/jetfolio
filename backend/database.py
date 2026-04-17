"""
Database Configuration and Session Management

This module sets up the SQLite database connection and provides
session management utilities for the application. Uses SQLModel
(Pydantic + SQLAlchemy) for ORM and database interactions.
"""

from sqlmodel import SQLModel, create_engine, Session

# Import all models to register their metadata with SQLModel
# This ensures all tables are created when create_db_and_tables() is called
from backend.models import (
    Stock,           # Individual stock holdings
    Theme,           # Investment themes/baskets
    StockTheme,      # Many-to-many relationship between stocks and themes
    PortfolioSnapshot,  # Historical portfolio value snapshots
    TimelineEvent,   # Significant events in portfolio history
    NewsArticle,     # Scraped news articles for stocks
    Config           # Application configuration and API keys
)

# Database configuration
sqlite_file_name = "portfolio.db"  # SQLite database file name
sqlite_url = f"sqlite:///{sqlite_file_name}"  # SQLite connection URL

# SQLite-specific connection arguments
# check_same_thread: False allows multi-threaded access (required for FastAPI)
connect_args = {"check_same_thread": False}

# Create database engine
# The engine manages the connection pool and dialect-specific behavior
# Increased pool size to handle background analysis threads
engine = create_engine(
    sqlite_url, 
    connect_args=connect_args,
    pool_size=20,
    max_overflow=20
)


def create_db_and_tables():
    """
    Create all database tables from SQLModel metadata.
    
    This function should be called once during application initialization
    to set up the database schema. It creates tables for all models
    imported above.
    
    Tables created:
        - stock: Portfolio holdings
        - theme: Investment themes/categories
        - stocktheme: Stock-theme relationships
        - portfoliosnapshot: Historical value tracking
        - timelineevent: Significant portfolio events
        - newsarticle: News data for stocks
        - config: Application settings and API keys
    
    Note: This is idempotent - safe to call multiple times.
          Existing tables won't be modified.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Dependency injection function for FastAPI endpoints.
    
    Yields a database session that is automatically closed after use.
    Use with FastAPI's Depends() for automatic session management.
    
    Example:
        @app.get("/api/stocks")
        def get_stocks(session: Session = Depends(get_session)):
            stocks = session.exec(select(Stock)).all()
            return stocks
    
    Yields:
        Session: SQLModel database session
    """
    with Session(engine) as session:
        yield session
