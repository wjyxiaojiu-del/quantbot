from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    PROJECT_NAME: str = "QuantBot"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://quant:quant@localhost:5432/quantbot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "quantbot-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Data Source: "baostock" | "eastmoney" | "akshare" | "mock"
    DATA_SOURCE: str = "mock"
    AKSHARE_TIMEOUT: int = 30
    DATA_BATCH_SIZE: int = 1000


@lru_cache()
def get_settings() -> Settings:
    return Settings()
