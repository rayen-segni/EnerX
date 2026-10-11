"""
EnerX Backend - Configuration Module
Loads application settings and environment variables with sensible defaults.
"""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL Database Settings
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    # Hedera Network Settings
    HEDERA_NETWORK: str = "testnet"
    OPERATOR_ID: str
    OPERATOR_KEY: str
    HEDERA_USER_1_KEY: str
    HEDERA_USER_2_KEY: str
    HEDERA_USER_3_KEY: str
    HEDERA_REVENUE_CONTRACT_ID: str | None = None
    
    # Data Paths
    PORTAL_USERS_PATH: str = "data/hedera_portal_users.json"
    SIMULATED_PRODUCTION_PATH: str = "data/simulated_production.json"
    CONTRACT_SOURCE_PATH: str = "contracts/RevenueDistribution.sol"
    
    @property
    def get_users(self) -> dict[int, str]:
        """Return a dictionary mapping user IDs to their Hedera private keys."""
        return {
            1: self.HEDERA_USER_1_KEY,
            2: self.HEDERA_USER_2_KEY,
            3: self.HEDERA_USER_3_KEY,
        }

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()  # type: ignore
