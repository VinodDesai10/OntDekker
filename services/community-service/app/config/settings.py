from pydantic_settings import BaseSettings
from typing import List
from shared.config import CommonSettings

class Settings(CommonSettings):
    SERVICE_NAME: str = "community-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/community_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # MinIO configuration — values injected by Docker Compose
    # MINIO_ENDPOINT: internal Docker hostname used by the SDK (e.g. minio:9000)
    MINIO_ENDPOINT: str = "minio:9000"
    # MINIO_PUBLIC_ENDPOINT: host:port embedded in presigned URLs returned to
    # the browser. Must be reachable from the client (e.g. localhost:9000).
    MINIO_PUBLIC_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    # CORS — list of origins permitted to make cross-origin requests.
    # Default permits the Next.js local development server.
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
