from pydantic_settings import BaseSettings
from shared.config import CommonSettings

class Settings(CommonSettings):
    SERVICE_NAME: str = "chat-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/chat_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
