from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import Dict, Any

from app.config.settings import settings
from app.database.engine import engine
from app.database.session import async_session
from app.api.auth import router as auth_router
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

# CORS — must be registered before other middleware and routes.
# Origins are configured via ALLOWED_ORIGINS in settings (env-backed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Mount authentication router — internal path: /auth/*
# External path via Traefik: /api/v1/authentication/auth/*
app.include_router(auth_router)


@app.get("/health", response_model=Dict[str, Any])
async def health_check(db=Depends(get_db)):
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "service": settings.SERVICE_NAME, "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "service": settings.SERVICE_NAME, "database": "disconnected", "error": str(e)}
