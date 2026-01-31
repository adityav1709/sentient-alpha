import uuid
from datetime import datetime
from typing import List, Optional
from enum import Enum as PyEnum

from sqlalchemy import String, Float, ForeignKey, Text, DateTime, JSON, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

from app.domain.constants import TradeAction

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_admin: Mapped[bool] = mapped_column(default=False)
    avatar_id: Mapped[int] = mapped_column(default=1) # 1-8 for static icons
    
    # Profile Details
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    linkedin_handle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    twitter_handle: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Relationships
    agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="owner")

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, default="gemini") # e.g. "gemini"
    persona: Mapped[str] = mapped_column(Text, default="You are a rational profit-maximizing trader.")
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    
    # Relationships
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="agents")
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="agent", cascade="all, delete-orphan")

    @property
    def owner_username(self) -> Optional[str]:
        return self.owner.username if self.owner else None

class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), unique=True)
    cash_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    total_equity: Mapped[float] = mapped_column(Float, default=10000.0) # updated periodically
    
    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="portfolio")
    positions: Mapped[List["Position"]] = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    trades: Mapped[List["Trade"]] = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")

class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=True) # Updated by scheduler
    
    @property
    def unrealized_pnl(self) -> float:
        if self.current_price is not None:
            return (self.current_price - self.avg_cost) * self.quantity
        return 0.0
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"))
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[TradeAction] = mapped_column(String, nullable=False) # stored as string
    quantity: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pnl_realized: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="trades")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"))
    prompt: Mapped[dict] = mapped_column(JSON) # Store raw JSON prompt
    response: Mapped[dict] = mapped_column(JSON) # Store raw JSON response
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="audit_logs")
