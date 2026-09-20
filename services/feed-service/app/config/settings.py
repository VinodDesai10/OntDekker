from pydantic_settings import BaseSettings
from shared.config import CommonSettings

class Settings(CommonSettings):
    SERVICE_NAME: str = "feed-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/feed_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # MinIO configuration — values injected by Docker Compose
    # MINIO_ENDPOINT: internal Docker hostname used for backend-to-MinIO SDK calls
    # MINIO_PUBLIC_ENDPOINT: browser-accessible host used in presigned URLs and media_url
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_PUBLIC_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    # Community Service — used for membership verification on COMMUNITY posts
    # Docker Compose internal hostname; override via .env in production
    COMMUNITY_SERVICE_URL: str = "http://community-service:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
