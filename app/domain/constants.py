from enum import Enum

class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
