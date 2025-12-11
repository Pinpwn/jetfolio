from abc import ABC, abstractmethod
from typing import List
from backend.models import Stock

class BaseAdapter(ABC):
    """
    Abstract base class for stock sync adapters.
    Every platform (Zerodha, Vested, etc.) must implement this interface.
    """
    
    def __init__(self, api_key: str, api_secret: str = None):
        self.api_key = api_key
        self.api_secret = api_secret

    @abstractmethod
    def authenticate(self):
        """
        Perform any necessary authentication (e.g., getting a session token).
        """
        pass

    @abstractmethod
    def fetch_holdings(self) -> List[Stock]:
        """
        Fetch holdings from the platform and return them as a list of Stock models.
        """
        pass
