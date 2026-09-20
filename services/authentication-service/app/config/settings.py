from pydantic_settings import BaseSettings
from typing import List
from shared.config import CommonSettings

class Settings(CommonSettings):
    SERVICE_NAME: str = "authentication-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/auth_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # OTP — short-lived email verification codes.
    OTP_EXPIRE_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    # CORS — comma-separated list of allowed origins.
    # Default permits the Next.js local development server.
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # SMTP — outbound email delivery for OTP and transactional messages.
    # All values must be supplied via environment variables in production.
    # Never commit real credentials — use .env.example as reference only.
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@ontdekker.com"
    SMTP_FROM_NAME: str = "OntDekker"
    # When True, STARTTLS is used on the plain port (587).
    # Set to False only for unencrypted relay in controlled environments.
    SMTP_USE_TLS: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
