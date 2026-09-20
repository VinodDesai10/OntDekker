from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from app.config.settings import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.ENVIRONMENT == "development"
)
