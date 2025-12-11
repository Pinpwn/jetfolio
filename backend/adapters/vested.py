import random
from typing import List
from backend.models import Stock
from backend.adapters.base import BaseAdapter

class VestedAdapter(BaseAdapter):
    def authenticate(self):
        print(f"Authenticating Vested Adapter with Key: {self.api_key}")
        pass

    def fetch_holdings(self) -> List[Stock]:
        print("Fetching holdings from Vested...")
        # Mock data for Vested (US Stocks)
        
        # Mock data disabled for production
        print("Vested API not implemented. Returning empty list.")
        return []
