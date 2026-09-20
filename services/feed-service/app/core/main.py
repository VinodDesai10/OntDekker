from fastapi import FastAPI, Depends
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import Dict, Any

from app.config.settings import settings
from app.database.engine import engine
from app.database.session import async_session
from app.api import api_router
from shared import register_exception_handlers, setup_logging
from shared.dependencies import get_request_id, get_db

setup_logging(service_name=settings.SERVICE_NAME, log_level="INFO")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bind sessionmaker to app state so dependencies can extract it
    app.state.db_sessionmaker = async_session
    yield
    # Dispose of connection pool on shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.SERVICE_NAME.replace("-", " ").title(),
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(get_request_id)]
)

register_exception_handlers(app)

# Include API routes
app.include_router(api_router)

@app.get("/health", response_model=Dict[str, Any])
async def health_check(db=Depends(get_db)):
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "service": settings.SERVICE_NAME, "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "service": settings.SERVICE_NAME, "database": "disconnected", "error": str(e)}
