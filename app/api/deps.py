from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core import security
from app.core.config import settings
from app.domain.models import User
from app.domain.schemas import TokenData
from app.core.database import SessionLocal

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

async def get_db() -> Generator:
    async with SessionLocal() as session:
        yield session

async def get_current_user(
    session: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenData(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    result = await session.execute(select(User).where(User.id == int(token_data.sub))) # sub store ID
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

from app.services.trading_service import TradingService
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.yahoo_finance_adapter import YahooFinanceAdapter

def get_trading_service(session: AsyncSession = Depends(get_db)) -> TradingService:
    return TradingService(
        db_session=session,
        llm_client=GeminiAdapter(),
        market_data_client=YahooFinanceAdapter()
    )
