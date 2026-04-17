"""
Real Zerodha adapter using Kite Connect API.
"""
from typing import List, Optional
from kiteconnect import KiteConnect
from backend.models import Stock
from backend.adapters.base import BaseAdapter
from backend.logger import logger
from sqlmodel import Session, select
from backend.models import Config
from backend.database import engine

class ZerodhaAdapter(BaseAdapter):
    def __init__(self, api_key: str = None):
        super().__init__(api_key)
        self.kite = None
        self.access_token = None
        self.user_id = None
        
    def _load_credentials(self):
        """Load API key and access token from Environment or Config"""
        import os
        
        # 1. Try Environment Variables first
        self.api_key = os.getenv('ZERODHA_API_KEY')
        self.access_token = os.getenv('ZERODHA_ACCESS_TOKEN')
        self.user_id = os.getenv('ZERODHA_USER_ID')
        
        # 2. Fallback to Config Table if not in environment
        with Session(engine) as session:
            if not self.api_key:
                api_key_config = session.get(Config, "zerodha_api_key")
                if api_key_config:
                    self.api_key = api_key_config.value
            
            if not self.access_token:
                token_config = session.get(Config, "zerodha_access_token")
                if token_config:
                    self.access_token = token_config.value
            
            if not self.user_id:
                user_config = session.get(Config, "zerodha_user_id")
                if user_config:
                    self.user_id = user_config.value
                
    def authenticate(self):
        """Authenticate using stored access token"""
        try:
            self._load_credentials()
            
            if not self.api_key:
                logger.warning("Zerodha API key not configured. Using mock data.")
                return False
                
            if not self.access_token:
                logger.warning("Zerodha access token not found. Need OAuth login.")
                return False
            
            # Initialize Kite Connect client
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            
            # Verify token by making a test API call
            profile = self.kite.profile()
            logger.info(f"Zerodha authenticated successfully for user: {profile.get('user_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Zerodha authentication failed: {e}")
            return False

    def fetch_holdings(self) -> List[Stock]:
        """Fetch holdings from Zerodha via Kite Connect API"""
        try:
            # Try real API if authenticated
            if self.kite and self.access_token:
                logger.info("Fetching real holdings from Zerodha...")
                holdings = self.kite.holdings()
                
                stocks = []
                for holding in holdings:
                    stock = Stock(
                        symbol=holding.get('tradingsymbol'),
                        name=holding.get('tradingsymbol'),  # Kite doesn't provide full name
                        quantity=holding.get('quantity', 0),
                        average_price=holding.get('average_price', 0.0),
                        current_price=holding.get('last_price', holding.get('average_price', 0.0)),
                        currency="INR",
                        platform="zerodha",
                        asset_class="EQUITY" if holding.get('product') == "CNC" else holding.get('product', 'EQUITY'),
                        previous_close=holding.get('close_price')
                    )
                    stocks.append(stock)
                
                logger.info(f"Fetched {len(stocks)} holdings from Zerodha")
                return stocks
                return stocks
            else:
                logger.warning("Zerodha not authenticated. Returning empty list.")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching Zerodha holdings: {e}")
            return []
