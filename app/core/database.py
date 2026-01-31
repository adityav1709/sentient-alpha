from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

# If using postgres, we need to pass ssl=True for Neon/Vercel
connect_args = {}
if settings.DATABASE_URL.startswith(("postgres://", "postgresql://")):
    connect_args = {"ssl": True}

engine = create_async_engine(settings.ASYNC_DATABASE_URL, connect_args=connect_args)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
