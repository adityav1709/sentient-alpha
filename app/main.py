from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from app.core.config import settings
from app.api import routes, deps
from app.services.scheduler_service import SchedulerService
from app.domain.models import Base

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

scheduler_service = SchedulerService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Database...")
    from app.core.database import engine, SessionLocal
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed Admin User
    async with SessionLocal() as session:
        from app.domain.models import User
        from app.core.security import get_password_hash
        from sqlalchemy import select
        
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalars().first()
        if not admin:
            logger.info("creating default admin user")
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin"),
                is_admin=True
            )
            session.add(admin_user)
            await session.commit()
            logger.info("Default admin user created (admin/admin)")
        
        # Seed Initial Agents
        from app.domain.models import Agent, Portfolio
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        
        if not agents and admin:
            logger.info("Seeding default agents...")
            
            # Agent 1: AlphaBot
            agent1 = Agent(
                name="AlphaBot",
                provider="gemini", 
                persona="You are a simplified momentum trader.",
                owner_id=admin.id
            )
            session.add(agent1)
            
            # Agent 2: MarketMaker
            agent2 = Agent(
                name="MarketMaker",
                provider="gemini",
                persona="You are a high-frequency liquidity provider.",
                owner_id=admin.id
            )
            session.add(agent2)
            
            await session.flush() # Generate IDs
            
            # Portfolios
            p1 = Portfolio(agent_id=agent1.id, cash_balance=100000.0, total_equity=100000.0)
            p2 = Portfolio(agent_id=agent2.id, cash_balance=500000.0, total_equity=500000.0)
            
            session.add(p1)
            session.add(p2)
            
            await session.commit()
            logger.info("Seeded agents: AlphaBot, MarketMaker")

    logger.info("Starting Scheduler...")
    await scheduler_service.start()
    
    yield
    
    # Shutdown
    await scheduler_service.shutdown()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

from app.api.endpoints import auth
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(routes.router, prefix=settings.API_V1_STR)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def root():
    return FileResponse("app/static/index.html")
