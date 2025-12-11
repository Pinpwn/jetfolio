"""
Enhanced News Scraper with yfinance integration.
"""
import yfinance as yf
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import random
from backend.logger import logger

class NewsScraperService:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
        self.trust_scores = {
            "Economic Times": 9,
            "MoneyControl": 8,
            "Business Standard": 8,
            "Financial Express": 7,
            "Google Finance": 7,
            "Yahoo Finance": 6,
            "Default": 5
        }
    
    def fetch_news_for_stock(self, symbol: str, stock_name: str = "") -> List[Dict]:
        """Fetch news from multiple sources"""
        all_news = []
        
        # Source 1: Google Finance (RSS/Search)
        try:
            news_google = self._scrape_google_finance(symbol)
            all_news.extend(news_google)
        except Exception as e:
            logger.warning(f"Google Finance scraping failed for {symbol}: {e}")
        
        # Source 2: MoneyControl (simplified - would need proper HTML parsing)
        try:
            news_mc = self._scrape_moneycontrol(symbol)
            all_news.extend(news_mc)
        except Exception as e:
            logger.warning(f"MoneyControl scraping failed for {symbol}: {e}")
        
        # If no news found, return empty list (no dummy data)
        if not all_news:
            logger.warning(f"No news scraped for {symbol}. Returning empty.")
            return []
        
        # Deduplicate
        deduplicated = self._deduplicate_news(all_news)
        logger.info(f"Fetched {len(all_news)} articles, {len(deduplicated)} after dedup for {symbol}")
        
        return deduplicated
    
    
    def _scrape_google_finance(self, symbol: str) -> List[Dict]:
        """Fetch news from yfinance (replaces Google Finance)"""
        try:
            # Map symbol
            yahoo_symbol = symbol
            if not symbol.endswith(".NS") and not symbol.endswith(".BO") and (symbol.isupper() and len(symbol) < 10): 
                 # Heuristic: If it looks like a US ticker (e.g. MSFT, AAPL, GOOGL, AMZN, TSLA, NVDA), don't append .NS
                 known_us_tickers = {"MSFT", "AAPL", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC", "CSCO", "ADBE", "PYPL", "PEP", "COST", "TMUS", "AVGO", "TXN", "CHTR", "QCOM", "SBUX", "AMGN", "INTU", "ISRG", "MDLZ", "GILD", "FISV", "BKNG", "ADP", "ATVI", "VRTX", "REGN", "ILMN", "KHC", "MNST", "KDP", "AEP", "WBA", "BIDU", "BIIB", "SNPS", "MELI", "DOCU", "SPLK", "ALGN", "WDAY", "MTCH", "ROST", "CTSH", "EBAY", "EA", "EXC", "LULU", "MAR", "XEL", "NXPI", "ORLY", "MRVL", "CTAS", "KLAC", "PCAR", "ANSS", "DXCM", "MCHP", "CDNS", "ALXN", "CERN", "CPRT", "DLTR", "FAST", "FOX", "FOXA", "IDXX", "LBTYA", "LBTYK", "MXIM", "NTAP", "PAYX", "SGEN", "SIRI", "SWKS", "TCOM", "VRSK", "VRSN", "WDC", "XRAY", "ZS", "OKTA", "PANW", "CRWD", "DDOG", "NET", "TEAM", "MDB", "SNOW", "PLTR", "U", "NTSK", "SNDK"}
                 
                 if symbol in known_us_tickers:
                     yahoo_symbol = symbol
                 else:
                     yahoo_symbol = f"{symbol}.NS"
            
            ticker = yf.Ticker(yahoo_symbol)
            news = ticker.news
            
            formatted_news = []
            for item in news:
                # yfinance news items are dicts:
                # {'uuid': '...', 'title': '...', 'publisher': '...', 'link': '...', 'providerPublishTime': 162...}
                
                pub_time = datetime.fromtimestamp(item.get('providerPublishTime', time.time()))
                
                formatted_news.append({
                    "title": item.get('title') or "No Title",
                    "summary": None, # yfinance doesn't usually provide summary in .news list
                    "source": item.get('publisher') or "Unknown Source",
                    "url": item.get('link') or "#",
                    "published_date": pub_time,
                    "sentiment": "neutral",
                    "credibility_score": self.trust_scores.get(item.get('publisher'), self.trust_scores["Default"])
                })
                
            logger.info(f"Fetched {len(formatted_news)} articles from yfinance for {yahoo_symbol}")
            return formatted_news
            
        except Exception as e:
            logger.error(f"yfinance news error for {symbol}: {e}")
            return []

    def _parse_rss_date(self, date_str: str) -> datetime:
        # Deprecated
        return datetime.utcnow()
    
    def _scrape_moneycontrol(self, symbol: str) -> List[Dict]:
        # Deprecated
        return []
    
    async def fetch_news(self, symbol: str) -> List[Dict]:
        """
        Legacy fetch_news wrapper. 
        Now redirects to fetch_stock_news from yfinance for consistency/speed.
        """
        # For now, keep using the robust yfinance news as the fast default
        return self.fetch_news_for_stock(symbol)

    async def fetch_comprehensive_intelligence(self, symbol: str, llm_service) -> Dict:
        """
        Fetches comprehensive intelligence using Perplexity.
        
        Args:
            symbol (str): Stock symbol.
            llm_service (LLMService): Instance to call Perplexity.
        
        Returns:
            Dict: Aggregated intelligence report.
        """
        logger.info(f"Fetching Deep Intelligence for {symbol}...")
        
        # Construct Deep Dive Prompts for Perplexity
        prompts = {
            "political": f"Investigate the current political winds and geopolitical risks associated with {symbol} stock. Include government policies, trade wars, and regulatory changes.",
            "macro": f"Analyze the macroeconomic factors affecting {symbol}. Interest rates, inflation contexts, and global supply chain shifts."
        }
        
        results = {}
        
        # Execute Perplexity Searches
        for key, prompt in prompts.items():
            try:
                # Use Perplexity via LLMService
                resp = await llm_service.get_response(prompt)
                results[key] = resp
            except Exception as e:
                logger.error(f"Failed to fetch {key} intelligence: {e}")
                results[key] = "Data unavailable."
        
        return results
    
    def _deduplicate_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        Deduplicate news using title similarity.
        Keep highest trust source, or contrasting opinions.
        """
        if len(news_list) <= 1:
            return news_list
        
        # Group similar articles
        groups = []
        for article in news_list:
            added = False
            for group in groups:
                # Check similarity with first article in group
                similarity = self._title_similarity(article["title"], group[0]["title"])
                if similarity > 0.7:  # 70% similar
                    group.append(article)
                    added = True
                    break
            if not added:
                groups.append([article])
        
        # For each group, keep best source OR contrasting opinions
        final_news = []
        for group in groups:
            if len(group) == 1:
                final_news.append(group[0])
            else:
                # Sort by trust score
                sorted_group = sorted(
                    group,
                    key=lambda x: self.trust_scores.get(x["source"], self.trust_scores["Default"]),
                    reverse=True
                )
                
                # Keep highest trust source
                final_news.append(sorted_group[0])
                
                # Check if there are contrasting sentiments
                sentiments = [a.get("sentiment", "neutral") for a in sorted_group]
                if "positive" in sentiments and "negative" in sentiments:
                    # Keep one contrasting article
                    for article in sorted_group[1:]:
                        if article.get("sentiment") != sorted_group[0].get("sentiment"):
                            final_news.append(article)
                            break
        
        return final_news
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        if not title1 or not title2:
             return 0.0
        return SequenceMatcher(None, str(title1).lower(), str(title2).lower()).ratio()
    
    def fetch_stock_analysis(self, symbol: str) -> Dict[str, Any]:
        """Legacy method - returns analysis data (no dummy news)"""
        screener_url = f"https://www.screener.in/company/{symbol}/consolidated/"
        
        links = [
            {"name": "Screener.in", "url": screener_url},
            {"name": "Economic Times", "url": f"https://economictimes.indiatimes.com/topic/{symbol}"},
            {"name": "Google Finance", "url": f"https://www.google.com/finance/quote/{symbol}:NSE"}
        ]
        
        sentiment = random.choice(["Bullish", "Neutral", "Bearish"])
        
        analyst_ratings = {
            "buy": random.randint(5, 20),
            "hold": random.randint(2, 10),
            "sell": random.randint(0, 5),
            "consensus": sentiment
        }
        
        # Fetch real news only (no fallback)
        news_articles = self.fetch_news_for_stock(symbol)
        news = [
            {
                "title": article["title"],
                "source": article["source"],
                "time": "Recently"
            }
            for article in news_articles[:3]
        ]
        
        return {
            "symbol": symbol,
            "links": links,
            "analyst_ratings": analyst_ratings,
            "latest_news": news,
            "sentiment": sentiment
        }
