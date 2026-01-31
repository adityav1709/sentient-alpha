from app.repositories.base import BaseRepository
from app.domain.models import Trade
from app.domain.schemas import TradeRead

class TradeRepository(BaseRepository[Trade, TradeRead, TradeRead]):
    pass
