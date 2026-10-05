"""
EnerX Backend - Configuration Module
Loads application settings and environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "EnerX Backend"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["*"]

    # PostgreSQL Database Settings
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5433
    DATABASE_NAME: str = "enerx"
    DATABASE_USER: str = "rayen"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_URL: Optional[str] = None

    # Hedera Network Settings
    HEDERA_NETWORK: str = "testnet"
    HEDERA_OPERATOR_ID: Optional[str] = None
    HEDERA_OPERATOR_KEY: Optional[str] = None
    HEDERA_MIRROR_NODE_URL: str = "https://testnet.mirrornode.hedera.com"

    # Data Paths
    PORTAL_USERS_PATH: str = "data/hedera_portal_users.json"
    SIMULATED_PRODUCTION_PATH: str = "data/simulated_production.json"
    CONTRACT_SOURCE_PATH: str = "contracts/RevenueDistribution.sol"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def sync_database_url(self) -> str:
        """Returns standard PostgreSQL connection string for psycopg3."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DATABASE_PASSWORD:
            return (
                f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@"
                f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        return (
            f"postgresql://{self.DATABASE_USER}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def alembic_database_url(self) -> str:
        """Returns SQLAlchemy URL format for Alembic migrations with psycopg3 driver."""
        url = self.sync_database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Returns cached settings instance."""
    return Settings()


settings = get_settings()
