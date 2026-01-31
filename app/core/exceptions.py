class SentientAlphaException(Exception):
    """Base exception for the application."""
    pass

class MarketDataError(SentientAlphaException):
    """Raised when there is an issue fetching market data."""
    pass

class LLMGenerationError(SentientAlphaException):
    """Raised when the LLM fails to generate a valid response."""
    pass

class TradeExecutionError(SentientAlphaException):
    """Raised when a trade cannot be executed (e.g. insufficient funds, short selling rule)."""
    pass

class InsufficientFundsError(TradeExecutionError):
    """Raised when trying to buy without enough cash."""
    pass

class ShortSellingError(TradeExecutionError):
    """Raised when trying to sell more than held quantity."""
    pass
