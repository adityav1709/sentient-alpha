import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from app.repositories.base import BaseRepository
from app.domain.models import Agent, Portfolio
from app.domain.schemas import AgentCreate, AgentRead

class AgentRepository(BaseRepository[Agent, AgentCreate, AgentCreate]):
    
    async def get_by_name(self, name: str) -> Optional[Agent]:
        result = await self.session.execute(select(Agent).where(Agent.name == name))
        return result.scalars().first()

    async def get_all_with_portfolios(self) -> list[Agent]:
        """Fetch all agents with their portfolios eagerly loaded."""
        stmt = select(Agent).options(
            selectinload(Agent.portfolio).selectinload(Portfolio.positions),
            selectinload(Agent.owner)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create_with_portfolio(self, obj_in: AgentCreate) -> Agent:
        """Create an agent and initialize their portfolio."""
        agent = Agent(name=obj_in.name, provider=obj_in.provider, persona=obj_in.persona)
        self.session.add(agent)
        await self.session.flush() # Get ID
        
        # Initialize Portfolio
        portfolio = Portfolio(agent_id=agent.id)
        self.session.add(portfolio)
        
        await self.session.commit()
        await self.session.refresh(agent)
        return agent
