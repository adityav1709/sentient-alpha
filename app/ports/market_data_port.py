from abc import ABC, abstractmethod
from typing import Dict, List

class MarketDataPort(ABC):
    
    @abstractmethod
    async def get_current_price(self, ticker: str) -> float:
        """Fetch the real-time price for a single ticker."""
        pass

    @abstractmethod
    async def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """Fetch real-time prices for multiple tickers. Returns a dict {ticker: price}."""
        pass
