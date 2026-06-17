"""
Analysis Manager - Handles background processing of pending news articles.
"""
import asyncio
import threading
from typing import List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.models import NewsArticle, Config
from backend.llm_service import LLMService
from backend.database import engine
from backend.logger import logger
from backend.security import get_secure_config

async def get_llm_service(session: AsyncSession) -> LLMService:
    """
    Helper to initialize LLMService with configured provider and credentials.
    """
    config_provider = await session.get(Config, "llm_provider")
    provider = get_secure_config().get_value(config_provider) if config_provider else "perplexity"
    
    # Initialize defaults
    api_key = None
    model = None
    ollama_url = None
    
    if provider == "perplexity":
        config_key = await session.get(Config, "perplexity_api_key")
        api_key = get_secure_config().get_value(config_key) if config_key else None
    elif provider == "groq":
        config_key = await session.get(Config, "groq_api_key")
        api_key = get_secure_config().get_value(config_key) if config_key else None
        config_model = await session.get(Config, "groq_model")
        model = get_secure_config().get_value(config_model) if config_model else "llama3-8b-8192"
    elif provider == "local":
        config_ollama = await session.get(Config, "ollama_url")
        ollama_url = get_secure_config().get_value(config_ollama) if config_ollama else None

    return LLMService(
        api_key=api_key, 
        provider=provider, 
        model=model, 
        ollama_url=ollama_url
    )

class AnalysisManager:
    """
    Manages background analysis of fetched news articles using LLMService.
    Ensures state tracking (pending -> processing -> completed) to handle restarts.
    """
    
    def __init__(self):
        pass



    async def process_pending_articles(self):
        """
        Fetch 'pending' articles from DB and run LLM analysis in a loop.
        Replaces recursion with a while loop for predictable behavior.
        """
        logger.info("[AnalysisManager] Starting background analysis loop...")
        
        while True:
            try:
                async with AsyncSession(engine) as session:
                    # Get pending articles - Limit to 5 at a time
                    query = select(NewsArticle).where(NewsArticle.processing_status == "pending").limit(5)
                    pending_articles = (await session.exec(query)).all()
                    
                    if not pending_articles:
                        logger.info("[AnalysisManager] No pending articles to process.")
                        break

                    logger.info(f"[AnalysisManager] Found {len(pending_articles)} pending articles.")
                    
                    # Initialize LLM Service using helper
                    llm = await get_llm_service(session)

                    for article in pending_articles:
                        try:
                            # Mark as processing
                            article.processing_status = "processing"
                            session.add(article)
                            await session.commit()
                            
                            # Run Analysis (Async)
                            logger.info(f"[AnalysisManager] Analyzing: {article.title[:30]}...")
                            sentiment = await llm.analyze_sentiment(article.title)
                            
                            # Update article
                            article.sentiment = sentiment
                            article.processing_status = "completed"
                            session.add(article)
                            await session.commit()
                            
                            logger.info(f"[AnalysisManager] Completed: {article.title[:30]} -> {sentiment}")
                            
                        except Exception as e:
                            logger.error(f"[AnalysisManager] Failed to analyze article {article.id}: {e}")
                            article.processing_status = "failed"
                            session.add(article)
                            await session.commit()
                    
                    # Small delay to yield control if needed
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"[AnalysisManager] Global error in analysis loop: {e}")
                break
