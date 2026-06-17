"""
Database Configuration and Session Management

This module sets up the SQLite database connection and provides
session management utilities for the application. Uses SQLModel
(Pydantic + SQLAlchemy) for ORM and database interactions.
"""

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

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
sqlite_url = f"sqlite:///{sqlite_file_name}"  # Synchronous URL for migrations
async_sqlite_url = f"sqlite+aiosqlite:///{sqlite_file_name}"  # Async URL

# SQLite-specific connection arguments
# check_same_thread: False allows multi-threaded access (required for FastAPI)
connect_args = {"check_same_thread": False}

# Create synchronous database engine for table creation/migrations
sync_engine = create_engine(
    sqlite_url, 
    connect_args=connect_args
)

# Create asynchronous database engine for application logic
engine = create_async_engine(
    async_sqlite_url,
    connect_args=connect_args
)


def create_db_and_tables():
    """
    Create all database tables from SQLModel metadata.
    """
    SQLModel.metadata.create_all(sync_engine)
    run_migrations()


def run_migrations():
    """
    Perform manual schema migrations for existing databases.
    """
    from sqlalchemy import text
    from backend.logger import logger
    try:
        with sync_engine.connect() as conn:
            # 1. Config table: Add is_encrypted
            res = conn.execute(text("PRAGMA table_info(config)"))
            columns = [row[1] for row in res.fetchall()]
            if 'is_encrypted' not in columns:
                logger.info("Migration: Adding 'is_encrypted' to config")
                conn.execute(text("ALTER TABLE config ADD COLUMN is_encrypted BOOLEAN DEFAULT 0"))
            
            # 2. Stock table: Add last_analyzed
            res_stock = conn.execute(text("PRAGMA table_info(stock)"))
            columns_stock = [row[1] for row in res_stock.fetchall()]
            if 'last_analyzed' not in columns_stock:
                logger.info("Migration: Adding 'last_analyzed' to stock")
                conn.execute(text("ALTER TABLE stock ADD COLUMN last_analyzed DATETIME"))
                
            conn.commit()
    except Exception as e:
        logger.warning(f"Migration check failed: {e}")


async def get_session():
    """
    Dependency injection function for FastAPI endpoints.
    
    Yields an asynchronous database session that is automatically closed after use.
    Use with FastAPI's Depends() for automatic session management.
    
    Yields:
        AsyncSession: SQLModel asynchronous database session
    """
    async with AsyncSession(engine) as session:
        yield session
