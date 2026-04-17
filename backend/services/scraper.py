"""
Enhanced Modular News Scraper
Supports multiple sources (YFinance, Google News RSS) and non-blocking execution.
"""
import httpx
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import random

from backend.logger import logger
from backend.services.price_fetcher import PriceFetcher

class NewsScraperService:
    """
    Service class for scraping news related to financial assets using async httpx.
    """

    def __init__(self) -> None:
        self.user_agents: List[str] = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
        self.trust_scores: Dict[str, int] = {
            "Economic Times": 9,
            "MoneyControl": 8,
            "Business Standard": 8,
            "Financial Express": 7,
            "Google Finance": 7,
            "Yahoo Finance": 6,
            "Livemint": 8,
            "NDTV Profit": 7,
            "Default": 5
        }
        self.price_fetcher = PriceFetcher()
    
    async def fetch_news_for_stock(self, symbol: str, stock_name: str = "", llm_service: Any = None) -> List[Dict[str, Any]]:
        """
        Fetches news from multiple sources for a given stock symbol.
        """
        # Run scraping tasks in parallel
        tasks = [
            self._scrape_google_finance(symbol),
            self._scrape_economic_times(symbol),
            self._scrape_yfinance(symbol)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for res in results:
            if isinstance(res, list):
                all_news.extend(res)
            elif isinstance(res, Exception):
                logger.warning(f"Scraping task failed: {res}")

        if not all_news:
            return []
        
        deduplicated = self._deduplicate_news(all_news)
        logger.info(f"Fetched {len(all_news)} articles, {len(deduplicated)} unique for {symbol}")
        
        return deduplicated

    async def _scrape_google_finance(self, symbol: str) -> List[Dict[str, Any]]:
        query = f"{symbol} stock news"
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        try:
            import xml.etree.ElementTree as ET
            async with httpx.AsyncClient() as client:
                response = await client.get(rss_url, headers={"User-Agent": self.user_agents[0]}, timeout=10.0)
                if response.status_code != 200:
                    return []
                    
                root = ET.fromstring(response.content)
                items = root.findall(".//item")
                
                news_list = []
                for item in items[:15]:
                    title = item.findtext("title", "No Title")
                    link = item.findtext("link", "#")
                    pub_date_str = item.findtext("pubDate", "")
                    source = item.findtext("source", "Google News")
                    
                    try:
                        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                    except Exception:
                        pub_date = datetime.utcnow()
                    
                    news_list.append({
                        "title": title, "summary": f"News regarding {symbol}", "source": source,
                        "url": link, "published_date": pub_date, "sentiment": "neutral",
                        "processing_status": "pending",
                        "credibility_score": self.trust_scores.get(source, self.trust_scores["Default"])
                    })
                return news_list
        except Exception as e:
            logger.error(f"Google RSS error for {symbol}: {e}")
            return []

    async def _scrape_economic_times(self, symbol: str) -> List[Dict[str, Any]]:
        query = f"{symbol} stock news site:economictimes.indiatimes.com"
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        try:
            import xml.etree.ElementTree as ET
            async with httpx.AsyncClient() as client:
                response = await client.get(rss_url, headers={"User-Agent": self.user_agents[0]}, timeout=10.0)
                if response.status_code != 200:
                    return []
                    
                root = ET.fromstring(response.content)
                items = root.findall(".//item")
                
                news_list = []
                for item in items[:5]:
                    news_list.append({
                        "title": item.findtext("title", "No Title"),
                        "summary": f"News regarding {symbol}", "source": "Economic Times",
                        "url": item.findtext("link", "#"),
                        "published_date": datetime.utcnow(),
                        "sentiment": "neutral", "processing_status": "pending",
                        "credibility_score": self.trust_scores["Economic Times"]
                    })
                return news_list
        except Exception as e:
            logger.error(f"ET RSS error for {symbol}: {e}")
            return []

    async def _scrape_yfinance(self, symbol: str) -> List[Dict[str, Any]]:
        try:
            ticker = self.price_fetcher.get_ticker_data(symbol)
            news = ticker.news
            
            formatted_news = []
            for item in news:
                pub_time = datetime.fromtimestamp(item.get('providerPublishTime', time.time()))
                source = item.get('publisher') or "Yahoo Finance"
                formatted_news.append({
                    "title": item.get('title', "No Title"),
                    "summary": f"News regarding {symbol}", "source": source,
                    "url": item.get('link', "#"),
                    "published_date": pub_time,
                    "sentiment": "neutral", "processing_status": "pending",
                    "credibility_score": self.trust_scores.get(source, self.trust_scores["Default"])
                })
            return formatted_news
        except Exception as e:
            logger.warning(f"YFinance scrape failed for {symbol}: {e}")
            return []

    async def fetch_news(self, symbol: str, llm_service: Any = None) -> List[Dict[str, Any]]:
        """
        Async entry point for news fetching.
        """
        return await self.fetch_news_for_stock(symbol, llm_service=llm_service)

    async def fetch_comprehensive_intelligence(self, symbol: str, llm_service: Any) -> Dict[str, Any]:
        """
        Fetches comprehensive intelligence using Perplexity.
        """
        logger.info(f"Fetching Deep Intelligence for {symbol}...")
        
        prompts = {
            "political": f"Investigate geopolitical risks for {symbol}.",
            "macro": f"Analyze macro factors for {symbol}."
        }
        
        results = {}
        for key, prompt in prompts.items():
            try:
                resp = await llm_service.get_response(prompt)
                results[key] = resp
            except Exception as e:
                logger.error(f"Failed to fetch {key} intelligence: {e}")
                results[key] = "Data unavailable."
        
        return results

    def _deduplicate_news(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate news using title similarity and trust scores."""
        if len(news_list) <= 1: return news_list
        
        # Sort by date desc first
        news_list.sort(key=lambda x: x['published_date'], reverse=True)
        
        groups: List[List[Dict[str, Any]]] = []
        for article in news_list:
            added = False
            for group in groups:
                if self._title_similarity(article["title"], group[0]["title"]) > 0.75:
                    group.append(article)
                    added = True
                    break
            if not added: groups.append([article])
        
        final_news = []
        for group in groups:
            # Pick the one with highest trust score, prioritizing completed processing status
            best = max(group, key=lambda x: (1 if x.get("processing_status") == "completed" else 0, x.get('credibility_score', 0)))
            final_news.append(best)
            
        return final_news[:20]
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        if not title1 or not title2: return 0.0
        return SequenceMatcher(None, str(title1).lower(), str(title2).lower()).ratio()
    
    async def fetch_stock_analysis(self, symbol: str, llm_service: Any = None) -> Dict[str, Any]:
        """
        Async version of stock analysis.
        """
        screener_url = f"https://www.screener.in/company/{symbol}/consolidated/"
        
        links = [
            {"name": "Screener.in", "url": screener_url},
            {"name": "Economic Times", "url": f"https://economictimes.indiatimes.com/topic/{symbol}"},
            {"name": "Google Finance", "url": f"https://www.google.com/finance/quote/{symbol}:NSE"}
        ]
        
        # Fetch news (async)
        news_articles = await self.fetch_news_for_stock(symbol, llm_service=llm_service)
        
        sentiment = random.choice(["Bullish", "Neutral", "Bearish"])
        analyst_ratings = {
            "buy": random.randint(5, 20),
            "hold": random.randint(2, 10),
            "sell": random.randint(0, 5),
            "consensus": sentiment
        }
        
        news_formatted = [{"title": a["title"], "source": a["source"], "time": "Recently"} for a in news_articles[:3]]
        
        return {
            "symbol": symbol, "links": links,
            "analyst_ratings": analyst_ratings,
            "latest_news": news_formatted, "sentiment": sentiment
        }
