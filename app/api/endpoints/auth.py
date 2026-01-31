from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.domain.models import User
from app.domain.schemas import Token, UserCreate, UserRead, UserPublicRead

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(deps.get_db)
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    result = await session.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            subject=user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserRead)
async def register_user(
    user_in: UserCreate,
    session: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Register a new user."""
    result = await session.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
        
    user = User(
        username=user_in.username,
        hashed_password=security.get_password_hash(user_in.password),
        is_admin=False # Default false
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.get("/users/me", response_model=UserRead)
async def read_users_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get current user."""
    return current_user

@router.get("/users/{username}/public", response_model=UserPublicRead)
async def get_public_profile(
    username: str,
    session: AsyncSession = Depends(deps.get_db)
) -> Any:
    """Get public profile of a user."""
    from sqlalchemy.orm import selectinload
    from app.domain.models import Agent, Portfolio
    
    stmt = select(User).where(User.username == username).options(
        selectinload(User.agents).selectinload(Agent.portfolio).selectinload(Portfolio.positions)
    )
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
