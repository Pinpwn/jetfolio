import yfinance as yf
from datetime import datetime, timedelta
from backend.logger import logger

class CurrencyService:
    _instance = None
    _rate = 84.0 # Default fallback
    _last_fetched = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CurrencyService, cls).__new__(cls)
        return cls._instance

    def get_usd_inr_rate(self) -> float:
        """
        Fetch live USD to INR exchange rate. 
        Caches the rate for 1 hour to prevent rate limiting and latency.
        """
        now = datetime.utcnow()
        if self._last_fetched and (now - self._last_fetched) < timedelta(hours=1):
            return self._rate
            
        try:
            logger.info("Fetching live USDINR rate...")
            ticker = yf.Ticker("USDINR=X")
            # Use history() method which is more reliable for currency tickers
            # This avoids internal errors with currentTradingPeriod
            hist = ticker.history(period='1d')
            
            if not hist.empty:
                rate = hist['Close'].iloc[-1]
                
                if rate and rate > 50: # Basic sanity check (INR should be > 50)
                    self._rate = rate
                    self._last_fetched = now
                    logger.info(f"Updated USDINR rate: {rate}")
                else:
                    logger.warning(f"Fetched invalid rate {rate}, using fallback {self._rate}")
            else:
                logger.warning(f"No price data available, using fallback {self._rate}")
                
        except Exception as e:
            logger.error(f"Error fetching USDINR rate: {e}. Using fallback {self._rate}")
            
        return self._rate
