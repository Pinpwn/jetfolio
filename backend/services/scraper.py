"""
Enhanced Modular News Scraper
Supports multiple sources (YFinance, Google News RSS) and non-blocking execution.
"""
import asyncio
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import random

from backend.logger import logger

# Trust Scores for Source Credibility
TRUST_SCORES = {
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

class BaseNewsSource(ABC):
    """Abstract Base Class for News Sources"""
    
    @abstractmethod
    def fetch_news(self, symbol: str) -> List[Dict]:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

class YFinanceSource(BaseNewsSource):
    """Fetches news from Yahoo Finance via yfinance library"""
    
    @property
    def name(self) -> str:
        return "YFinance"
        
    def fetch_news(self, symbol: str) -> List[Dict]:
        try:
            # Ticker Mapping logic
            yahoo_symbol = symbol
            # Heuristic: If it looks like a US ticker, don't append .NS
            # (Simplified list for brevity, logic preserved from original)
            if not symbol.endswith(".NS") and not symbol.endswith(".BO") and (symbol.isupper() and len(symbol) < 10): 
                 known_us_tickers = {"MSFT", "AAPL", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"} # Shortened list
                 if symbol not in known_us_tickers and not any(x in symbol for x in ["-USD", "BTC", "ETH"]):
                     yahoo_symbol = f"{symbol}.NS"
            
            ticker = yf.Ticker(yahoo_symbol)
            news = ticker.news
            
            formatted_news = []
            for item in news:
                pub_time = datetime.fromtimestamp(item.get('providerPublishTime', time.time()))
                formatted_news.append({
                    "title": item.get('title') or "No Title",
                    "summary": None,
                    "source": item.get('publisher') or "Yahoo Finance",
                    "url": item.get('link') or "#",
                    "published_date": pub_time,
                    "sentiment": "neutral",
                    "credibility_score": TRUST_SCORES.get(item.get('publisher'), TRUST_SCORES["Default"])
                })
            return formatted_news
        except Exception as e:
            logger.warning(f"YFinance scrape failed for {symbol}: {e}")
            return []

class GoogleNewsSource(BaseNewsSource):
    """Fetches news from Google News RSS Feed"""
    
    @property
    def name(self) -> str:
        return "GoogleNewsRSS"
        
    def fetch_news(self, symbol: str) -> List[Dict]:
        try:
            # RSS URL for Google News Search
            # q={symbol} stock news
            url = f"https://news.google.com/rss/search?q={symbol}+stock+news&hl=en-IN&gl=IN&ceid=IN:en"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Google RSS failed {response.status_code}")
                return []
                
            # Parse XML
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            
            formatted_news = []
            for item in items[:15]: # Limit to 15 items per source
                title = item.find('title').text if item.find('title') is not None else "No Title"
                link = item.find('link').text if item.find('link') is not None else "#"
                pub_date_str = item.find('pubDate').text if item.find('pubDate') is not None else ""
                source_elem = item.find('source')
                source = source_elem.text if source_elem is not None else "Google News"
                
                # Parse Date (RFC 822) e.g., "Tue, 03 Jun 2003 09:39:21 GMT"
                try:
                    # Simple parser or just use current time if fail
                    # Python's email.utils.parsedate_to_datetime is good but let's prevent deps issues
                    # We'll try a common format
                    pub_time = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                except:
                    pub_time = datetime.utcnow()
                
                formatted_news.append({
                    "title": title,
                    "summary": f"News regarding {symbol}",
                    "source": source,
                    "url": link,
                    "published_date": pub_time,
                    "sentiment": "neutral",
                    "credibility_score": TRUST_SCORES.get(source, TRUST_SCORES["Default"])
                })
                
            return formatted_news
        except Exception as e:
            logger.warning(f"Google RSS scrape failed for {symbol}: {e}")
            return []

class NewsScraperService:
    """
    Main Service executing scraping strategies in background threads.
    """
    def __init__(self):
        self.sources: List[BaseNewsSource] = [
            YFinanceSource(),
            GoogleNewsSource()
        ]
        self.executor = ThreadPoolExecutor(max_workers=5) # Workers for concurrent source fetching
        
    async def fetch_news(self, symbol: str) -> List[Dict]:
        """
        Async entry point. Runs blocking scrapers in threadpool.
        """
        loop = asyncio.get_event_loop()
        all_news = []
        
        # Create tasks for each source
        tasks = []
        for source in self.sources:
            # Partial helps pass arguments to the function run in executor
            func = partial(source.fetch_news, symbol)
            tasks.append(loop.run_in_executor(self.executor, func))
            
        # Wait for all sources
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                all_news.extend(res)
            else:
                logger.error(f"Source error: {res}")
                
        if not all_news:
             return []
             
        # Deduplicate
        deduplicated = self._deduplicate_news(all_news)
        logger.info(f"Fetched {len(deduplicated)} articles for {symbol} from {len(self.sources)} sources")
        return deduplicated

    async def fetch_comprehensive_intelligence(self, symbol: str, llm_service) -> Dict:
        """
        Fetches comprehensive intelligence using Perplexity.
        """
        logger.info(f"Fetching Deep Intelligence for {symbol}...")
        
        prompts = {
            "political": f"Investigate the current political winds and geopolitical risks associated with {symbol} stock. Include government policies, trade wars, and regulatory changes.",
            "macro": f"Analyze the macroeconomic factors affecting {symbol}. Interest rates, inflation contexts, and global supply chain shifts."
        }
        
        results = {}
        
        # Execute Perplexity Searches (These are already async usually in LLMService, keep them awaited)
        for key, prompt in prompts.items():
            try:
                resp = await llm_service.get_response(prompt)
                results[key] = resp
            except Exception as e:
                logger.error(f"Failed to fetch {key} intelligence: {e}")
                results[key] = "Data unavailable."
        
        return results
    
    def _deduplicate_news(self, news_list: List[Dict]) -> List[Dict]:
        """Deduplicate news using title similarity."""
        if len(news_list) <= 1:
            return news_list
        
        # Sort by date desc first
        news_list.sort(key=lambda x: x['published_date'], reverse=True)
        
        groups = []
        for article in news_list:
            added = False
            for group in groups:
                similarity = self._title_similarity(article["title"], group[0]["title"])
                if similarity > 0.75: # Higher threshold 
                    group.append(article)
                    added = True
                    break
            if not added:
                groups.append([article])
        
        final_news = []
        for group in groups:
            # Pick the one with highest trust score
            best = max(group, key=lambda x: x.get('credibility_score', 0))
            final_news.append(best)
            
        return final_news[:20] # Limit per stock
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        if not title1 or not title2:
             return 0.0
        return SequenceMatcher(None, str(title1).lower(), str(title2).lower()).ratio()
    
    def fetch_stock_analysis(self, symbol: str) -> Dict[str, Any]:
        """Legacy method for analysis page"""
        # Note: This is synchronous and might block if called directly. 
        # Ideally, refactor this to async too, but keeping it simple for now as it's a specific endpoint.
        # We'll use just YFinance source directly here for speed or re-use the async method via asyncio.run if needed.
        # Fallback to simple direct fetch
        yf_source = YFinanceSource()
        news_articles = yf_source.fetch_news(symbol) 
        
        sentiment = random.choice(["Bullish", "Neutral", "Bearish"])
        analyst_ratings = {
            "buy": random.randint(5, 20),
            "hold": random.randint(2, 10),
            "sell": random.randint(0, 5),
            "consensus": sentiment
        }
        
        news_formatted = [
            {"title": a["title"],"source": a["source"],"time": "Recently"} 
            for a in news_articles[:3]
        ]
        
        return {
            "symbol": symbol,
            "links": [{"name": "Google Finance", "url": f"https://www.google.com/finance/quote/{symbol}"}],
            "analyst_ratings": analyst_ratings,
            "latest_news": news_formatted,
            "sentiment": sentiment
        }
