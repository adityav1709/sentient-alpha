from pydantic_settings import BaseSettings
from pydantic import ValidationError
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "SentientAlpha"
    API_V1_STR: str = "/api/v1"
    
    DOMAIN: str = "localhost"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sentient_alpha.db"

    # Security
    SECRET_KEY: str = "change_this_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # AI Provider
    GOOGLE_API_KEY: str

    # Market Data
    MARKET_DATA_PROVIDER: str = "yfinance"

    # Scheduling
    SCHEDULER_INTERVAL_SECONDS: int = 600

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Helper to ensure we use the async driver for SQLAlchemy."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("sqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
