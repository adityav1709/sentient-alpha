from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from uuid import UUID

from app.api import deps
from app.domain.schemas import AgentCreate, AgentRead, AgentDetail, UserRead, UserUpdate
from app.repositories.agent_repository import AgentRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.services.trading_service import TradingService
from app.domain.models import Agent, Portfolio, User

router = APIRouter()

@router.post("/agents/", response_model=AgentRead)
async def create_agent(
    agent_in: AgentCreate,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Create a new AI agent and initialize its portfolio."""
    repo = AgentRepository(Agent, session)
    existing = await repo.get_by_name(agent_in.name)
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this name already exists")
    
    # We need to update create_with_portfolio to accept owner_id or handle it here
    # Ideally repo method should be updated or we pass it in metadata
    # Let's update repo call. But wait, create_with_portfolio in repo expects AgentCreate.
    # We should update AgentCreate to optionally include owner_id OR handle it manually.
    # Simpler: Create agent instance manually here or update repo signature. 
    # Let's update Repo signature in next step or use manual creation.
    # Actually, let's just pass user to a modified repo method? 
    # Or better: modify AgentCreate at runtime? No, cleaner to update repo.
    # For now, let's inject owner_id.
    agent = Agent(
        name=agent_in.name, 
        provider=agent_in.provider, 
        persona=agent_in.persona,
        owner_id=current_user.id
    )
    session.add(agent)
    await session.flush()
    
    # Init Portfolio
    portfolio = Portfolio(agent_id=agent.id)
    session.add(portfolio)
    await session.commit()
    await session.commit()
    
    # Reload with portfolio for response model
    stmt = select(Agent).where(Agent.id == agent.id).options(
        selectinload(Agent.portfolio).selectinload(Portfolio.positions),
        selectinload(Agent.owner)
    )
    result = await session.execute(stmt)
    agent_loaded = result.scalars().first()
    
    return agent_loaded

@router.get("/agents/", response_model=List[AgentRead])
async def read_agents(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Retrieve all agents (Global Leaderboard)."""
    repo = AgentRepository(Agent, session)
    return await repo.get_all_with_portfolios()

@router.get("/agents/me", response_model=List[AgentRead])
async def read_my_agents(
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Retrieve agents owned by the current user."""
    stmt = select(Agent).where(Agent.owner_id == current_user.id).options(
        selectinload(Agent.portfolio).selectinload(Portfolio.positions),
        selectinload(Agent.owner)
    )
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/agents/{agent_id}", response_model=AgentDetail)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Get specific agent details."""
    
    # Eager load portfolio, positions, and trades to avoid MissingGreenlet
    stmt = select(Agent).where(Agent.id == agent_id).options(
        selectinload(Agent.portfolio).selectinload(Portfolio.positions),
        selectinload(Agent.portfolio).selectinload(Portfolio.trades), # Assuming trades on Portfolio
        selectinload(Agent.audit_logs),
        selectinload(Agent.owner)
    )
    result = await session.execute(stmt)
    agent = result.scalars().first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Flatten trades from portfolio to top level for schema matching if needed
    # or update schema to nested. 
    # AgentDetail expects trades directly? Let's check schema.
    # User asked for "trades of an agent".
    # AgentDetail definition: trades: List[TradeRead] = []
    # But trades are on portfolio.
    # Let's populate the Pydantic model manually or use a property.
    agent_detail = AgentDetail.model_validate(agent)
    if agent.portfolio and agent.portfolio.trades:
        agent_detail.trades = agent.portfolio.trades
        
    return agent_detail

@router.post("/market/cycle")
async def trigger_market_cycle(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_active_superuser),
    service: TradingService = Depends(deps.get_trading_service)
) -> Any:
    """Manually trigger a market cycle (async background task)."""
    background_tasks.add_task(service.execute_market_cycle)
    return {"message": "Market cycle triggered in background"}

# --- User Profile Endpoints ---

@router.get("/users/me", response_model=UserRead)
async def get_my_profile(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Get current user profile."""
    return current_user

@router.patch("/users/me", response_model=UserRead)
async def update_my_profile(
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
    session: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Update current user profile (avatar, etc.)."""
    if user_in.avatar_id is not None:
        current_user.avatar_id = user_in.avatar_id
    if user_in.first_name is not None:
        current_user.first_name = user_in.first_name
    if user_in.last_name is not None:
        current_user.last_name = user_in.last_name
    if user_in.linkedin_handle is not None:
        current_user.linkedin_handle = user_in.linkedin_handle
    if user_in.twitter_handle is not None:
        current_user.twitter_handle = user_in.twitter_handle
    
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return current_user
