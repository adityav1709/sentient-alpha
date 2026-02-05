from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import logging

from app.core.config import settings
from app.services.trading_service import TradingService
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.yahoo_finance_adapter import YahooFinanceAdapter

logger = logging.getLogger(__name__)

from app.core.database import engine, SessionLocal

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.gemini_client = GeminiAdapter()
        self.market_data_client = YahooFinanceAdapter()

    async def start(self):
        logger.info(f"Starting Scheduler with timezone {settings.SCHEDULER_TIMEZONE}...")
        
        # Market Cycle: Runs Monday-Friday during NASDAQ hours (9:30 AM - 4:00 PM ET)
        # Every 10 minutes (0, 10, 20, 30, 40, 50)
        self.scheduler.add_job(
            self.run_market_cycle, 
            'cron',
            day_of_week='mon-fri',
            hour='9-16',
            minute='*/10',
            timezone=settings.SCHEDULER_TIMEZONE,
            id='market_cycle',
            replace_existing=True,
            coalesce=True,
            max_instances=3
        )
        
        # High-Frequency Price Update Job (Every 10 min by default now)
        self.scheduler.add_job(
            self.run_price_update,
            'interval',
            seconds=settings.PRICE_UPDATE_INTERVAL_SECONDS,
            id='price_update',
            replace_existing=True,
            coalesce=True
        )
        self.scheduler.start()

    async def shutdown(self):
        logger.info("Shutting down Scheduler...")
        self.scheduler.shutdown()
        await self.engine.dispose()

    async def run_market_cycle(self):
        async with self.SessionLocal() as session:
            try:
                service = TradingService(
                    db_session=session,
                    llm_client=self.gemini_client,
                    market_data_client=self.market_data_client
                )
                await service.execute_market_cycle()
            except Exception as e:
                logger.error(f"Market Cycle Error: {e}", exc_info=True)

    async def run_price_update(self):
        # Lightweight job to just update equity/prices
        async with self.SessionLocal() as session:
            try:
                service = TradingService(
                    db_session=session,
                    llm_client=self.gemini_client,
                    market_data_client=self.market_data_client
                )
                await service.update_market_values()
            except Exception as e:
                logger.error(f"Price Update Error: {e}", exc_info=True)
