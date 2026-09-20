from pydantic_settings import BaseSettings
from functools import lru_cache

class CommonSettings(BaseSettings):
    JWT_SECRET: str = "default_secret_key_change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    KAFKA_URL: str = "localhost:9092"
    REDIS_URL: str = "redis://localhost:6379/0"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_common_settings() -> CommonSettings:
    return CommonSettings()
