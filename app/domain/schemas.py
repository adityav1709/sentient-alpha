from pydantic import BaseModel, Field, UUID4, ConfigDict
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Enums ---
from app.domain.constants import TradeAction

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    sub: Optional[str] = None

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    twitter_handle: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    avatar_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_handle: Optional[str] = None
    
class UserPublicRead(BaseModel):
    username: str
    avatar_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    linkedin_handle: Optional[str] = None
    twitter_handle: Optional[str] = None
    agents: List["AgentRead"] = []
    
    model_config = ConfigDict(from_attributes=True)

# --- LLM Output Schemas ---
class LLMTrade(BaseModel):
    action: TradeAction
    ticker: str
    quantity: int = Field(..., gt=0, description="Quantity to buy or sell. Must be positive.")

class LLMResponse(BaseModel):
    thoughts: str = Field(..., description="Reasoning behind the trade decisions.")
    trades: List[LLMTrade]

# --- Domain Schemas ---

class AuditLogRead(BaseModel):
    id: int
    prompt: Dict[str, Any]
    response: Dict[str, Any]
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PositionRead(BaseModel):
    ticker: str
    quantity: int
    avg_cost: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)

class TradeRead(BaseModel):
    id: int
    ticker: str
    action: TradeAction
    quantity: int
    price: float
    reasoning: str
    timestamp: datetime
    pnl_realized: Optional[float]

    model_config = ConfigDict(from_attributes=True)

class PortfolioRead(BaseModel):
    id: int
    cash_balance: float
    total_equity: float
    positions: List[PositionRead] = []

    model_config = ConfigDict(from_attributes=True)

class AgentCreate(BaseModel):
    name: str
    provider: str = "gemini"
    persona: str = "You are a rational profit-maximizing trader."

class AgentRead(BaseModel):
    id: UUID4
    name: str
    provider: str
    persona: str
    owner_username: Optional[str] = None
    portfolio: Optional[PortfolioRead] = None

    model_config = ConfigDict(from_attributes=True)

class AgentDetail(AgentRead):
    audit_logs: List[AuditLogRead] = []
    trades: List[TradeRead] = []
