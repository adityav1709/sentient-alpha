from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.domain.schemas import LLMResponse, PortfolioRead

class LLMPort(ABC):
    
    @abstractmethod
    async def generate_trade_decision(
        self, 
        agent_name: str,
        portfolio: PortfolioRead, 
        market_data: Dict[str, Any],
        rank: int,
        leader_gap: float,
        persona: str = "",
        news_context: str = ""
    ) -> LLMResponse:
        """
        Ask the LLM for trading decisions based on current portfolio, market data, and gamification context.
        """
        pass
