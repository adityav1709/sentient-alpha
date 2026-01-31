from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.domain.models import Portfolio
from app.domain.schemas import PortfolioRead # Using Read schema as generic Create/Update might be handled internally

class PortfolioRepository(BaseRepository[Portfolio, PortfolioRead, PortfolioRead]):
    
    async def get_by_agent_id(self, agent_id: UUID) -> Optional[Portfolio]:
        # Eager load positions for trading logic
        stmt = select(Portfolio).where(Portfolio.agent_id == agent_id).options(selectinload(Portfolio.positions))
        result = await self.session.execute(stmt)
        return result.scalars().first()
