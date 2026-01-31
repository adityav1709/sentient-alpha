import logging
import asyncio
from typing import List, Dict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Agent, Portfolio, Position, Trade, AuditLog
from app.domain.constants import TradeAction
from app.domain.schemas import LLMResponse, PortfolioRead, PositionRead
from app.ports.llm_port import LLMPort
from app.ports.market_data_port import MarketDataPort
from app.repositories.agent_repository import AgentRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.trade_repository import TradeRepository
from app.core.exceptions import InsufficientFundsError, ShortSellingError

logger = logging.getLogger(__name__)

class TradingService:
    def __init__(
        self,
        db_session: AsyncSession,
        llm_client: LLMPort,
        market_data_client: MarketDataPort
    ):
        self.db = db_session
        self.llm = llm_client
        self.market_data = market_data_client
        self.agent_repo = AgentRepository(Agent, db_session)
        self.portfolio_repo = PortfolioRepository(Portfolio, db_session)
        self.trade_repo = TradeRepository(Trade, db_session)

    async def update_market_values(self):
        """
        Fetches latest market data and updates Portfolio equity and Position prices.
        This is a lightweight operation compared to the full market cycle.
        """
        # 1. Fetch Agents
        agents = await self.agent_repo.get_all_with_portfolios()
        if not agents:
            return {}, []

        # 2. Gather all tickers to fetch prices efficiently
        # Expanded universe for a more active simulation
        all_tickers = set(["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMD", "META", "AMZN", "NFLX", "PYPL"]) 
        for agent in agents:
            if agent.portfolio:
                for pos in agent.portfolio.positions:
                    all_tickers.add(pos.ticker)
        
        # 3. Fetch Data
        logger.info(f"📊 Fetching Market Data for {len(all_tickers)} tickers...")
        t0 = datetime.utcnow()
        rich_data = await self.market_data.get_rich_market_data(list(all_tickers))
        fetch_duration = (datetime.utcnow() - t0).total_seconds()
        logger.info(f"   -> Data fetched in {fetch_duration:.2f}s")
        
        simple_prices = {t: d['price'] for t, d in rich_data.items()}

        # 4. Update Equity & Position Prices
        for agent in agents:
            if not agent.portfolio:
                continue
            
            equity = agent.portfolio.cash_balance
            for pos in agent.portfolio.positions:
                price = simple_prices.get(pos.ticker)
                
                # Update persisted price if available
                if price:
                    pos.current_price = price
                    equity += pos.quantity * price
                else:
                    # Fallback to last known or cost
                    fallback = pos.current_price or pos.avg_cost
                    equity += pos.quantity * fallback
            
            agent.portfolio.total_equity = equity
            
        await self.db.commit()
        return rich_data, agents

    async def execute_market_cycle(self):
        start_time = datetime.utcnow()
        logger.info(f"🚀 Starting Market Cycle at {start_time}")
        
        # Reuse the update logic
        rich_data, agents = await self.update_market_values()
        
        if not agents:
            logger.info("No agents found.")
            return

        logger.info(f"👥 Processing {len(agents)} agents...")
        
        all_tickers = list(rich_data.keys())
        simple_prices = {t: d['price'] for t, d in rich_data.items()}
        
        # 5. Calculate Leaderboard (based on just-updated equity)
        agent_equities = [(a.id, a.portfolio.total_equity) for a in agents if a.portfolio]
        agent_equities.sort(key=lambda x: x[1], reverse=True)
        
        leader_equity = agent_equities[0][1] if agent_equities else 0
        ranking_map = {aid: (rank, leader_equity - eq) for rank, (aid, eq) in enumerate(agent_equities, start=1)}

        # 6. Process Each Agent
        for agent in agents:
            if not agent.portfolio:
                continue
                
            rank, gap = ranking_map.get(agent.id, (0, 0.0))
            
            # Convert DB Portfolio to Pydantic for LLM
            # We explicitly construct it to ensure clean data passed
            positions_read = [
                PositionRead(
                    ticker=p.ticker,
                    quantity=p.quantity,
                    avg_cost=p.avg_cost,
                    current_price=p.current_price
                ) for p in agent.portfolio.positions
            ]
            portfolio_read = PortfolioRead(
                id=agent.portfolio.id,
                cash_balance=agent.portfolio.cash_balance,
                total_equity=agent.portfolio.total_equity,
                positions=positions_read
            )

            try:
                # 6. Get LLM Decision
                logger.info(f"   -> Asking Gemini for {agent.name}...")
                decision = await self.llm.generate_trade_decision(
                    agent_name=agent.name,
                    portfolio=portfolio_read,
                    market_data=rich_data, # Passing rich dict
                    rank=rank,
                    leader_gap=gap,
                    persona=agent.persona # Passing persona
                )

                logger.info("Fetching audit context")
                
                # 7. Audit Log (Full Context)
                # We store the exact data used for decision making
                audit_context = {
                    "identity": {
                        "name": agent.name,
                        "persona": agent.persona
                    },
                    "gamification": {
                        "rank": rank,
                        "gap_to_leader": gap
                    },
                    "portfolio": portfolio_read.model_dump(),
                    "market_data_snapshot": {k: v for k, v in rich_data.items() if k in all_tickers} # Store what was passed
                }
                
                logger.info("Audit context fetched")
                
                audit_log = AuditLog(
                    agent_id=agent.id,
                    prompt=audit_context,
                    response=decision.model_dump()
                )

                self.db.add(audit_log)
                # 8. Execute Trades
                for trade_req in decision.trades:
                    current_price = simple_prices.get(trade_req.ticker)
                    if not current_price:
                        logger.warning(f"Skipping trade for {trade_req.ticker}: No price data")
                        continue
                        
                    try:
                        await self._execute_trade(
                            agent.portfolio, 
                            trade_req.action, 
                            trade_req.ticker, 
                            trade_req.quantity, 
                            current_price, 
                            decision.thoughts
                        )
                    except (InsufficientFundsError, ShortSellingError) as e:
                        logger.warning(f"Trade rejected for {agent.name}: {e}")
            
                logger.info(f"   -> 🤖 {agent.name} (Rank #{rank}): {len(decision.trades)} Trades. Thoughts: {decision.thoughts[:50]}...")
            
            except Exception as e:
                logger.error(f"❌ Error processing agent {agent.name}: {e}")
                
        # 9. Commit all changes (Atomic Cycle)
        await self.db.commit()
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Market Cycle Completed in {duration:.2f}s | Success: {len(agents)} Agents")

    async def _execute_trade(
        self, 
        portfolio: Portfolio, 
        action: TradeAction, 
        ticker: str, 
        quantity: int, 
        price: float, 
        reasoning: str
    ):
        cost = quantity * price
        
        # Validation & Execution
        if action == TradeAction.BUY:
            if portfolio.cash_balance < cost:
                raise InsufficientFundsError(f"Need ${cost}, have ${portfolio.cash_balance}")
            
            portfolio.cash_balance -= cost
            
            # Update Position
            position = next((p for p in portfolio.positions if p.ticker == ticker), None)
            if position:
                # Weighted Avg Cost
                total_cost = (position.quantity * position.avg_cost) + cost
                position.quantity += quantity
                position.avg_cost = total_cost / position.quantity
            else:
                position = Position(
                    portfolio_id=portfolio.id,
                    ticker=ticker,
                    quantity=quantity,
                    avg_cost=price
                )
                portfolio.positions.append(position)
                
        elif action == TradeAction.SELL:
            position = next((p for p in portfolio.positions if p.ticker == ticker), None)
            if not position or position.quantity < quantity:
                held = position.quantity if position else 0
                raise ShortSellingError(f"Sell {quantity} {ticker} but hold {held}")
            
            portfolio.cash_balance += cost
            pnl = (price - position.avg_cost) * quantity
            
            position.quantity -= quantity
            if position.quantity == 0:
                # Remove position safely
                 # Using session.delete is safer than list removal for ORM
                await self.db.delete(position)
                # Also remove from local list to avoid processing again if needed (though we break usually)
                portfolio.positions.remove(position)
        
        # Record Trade
        trade = Trade(
            portfolio_id=portfolio.id,
            ticker=ticker,
            action=action.value, # Store enum value
            quantity=quantity,
            price=price,
            reasoning=reasoning,
            pnl_realized=pnl if action == TradeAction.SELL else None
        )
        self.db.add(trade)
