import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
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
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Data Source: "akshare" | "baostock" | "eastmoney" | "yfinance" | "mock"
    DATA_SOURCE: str = "akshare"
    AKSHARE_TIMEOUT: int = 30
    DATA_BATCH_SIZE: int = 1000

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        # 生产环境强制要求修改 SECRET_KEY
        if not os.getenv("DEBUG", "true").lower() == "true":
            if v in ("dev-secret-key-change-in-production", "quantbot-secret-key-change-in-production", ""):
                raise ValueError("生产环境必须设置 SECRET_KEY，不能使用默认值")
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()
