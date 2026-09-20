from pydantic_settings import BaseSettings
from typing import List
from shared.config import CommonSettings


class Settings(CommonSettings):
    SERVICE_NAME: str = "user-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/user_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    # MinIO — required for Phase 1 avatar/cover image upload
    # Credentials must be provided via environment variables in all environments.
    # No sensitive defaults are set here.
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_USE_SSL: bool = False
    MINIO_BUCKET_PROFILES: str = "profiles"
    # Max upload size in bytes (5 MB)
    MINIO_MAX_FILE_SIZE: int = 5 * 1024 * 1024
    # Browser-accessible MinIO hostname for presigned URL generation.
    # When set, presigned URLs are rewritten to use this host instead of
    # MINIO_ENDPOINT (which is the Docker-internal hostname unreachable by browsers).
    # Example: "localhost:9000" for local development.
    # In production this would be the public CDN/S3 hostname.
    # If empty, presigned URLs use MINIO_ENDPOINT as-is (only works when
    # the frontend runs inside the Docker network).
    MINIO_PUBLIC_URL: str = "localhost:9000"
    # CORS — comma-separated list of allowed origins.
    # Default permits the Next.js local development server.
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
