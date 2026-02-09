import logging
from pydantic_settings import BaseSettings
from environs import Env
from pathlib import Path


env = Env()


class AppConfig(BaseSettings):
    """Application config /settings."""

    # APP
    ENVIRONMENT: str = env.str("APP_ENVIRONMENT", "LOCAL")
    LOG_LEVEL: int = getattr(logging, env.str("APP_LOG_LEVEL", "ERROR"), logging.INFO)
    APP_URL: str = env.str("APP_URL")
    DOCS_URL: str = env.str("APP_DOCS_PATH", "/api/docs")
    REDOC_URL: str = env.str("APP_REDOC_PATH", "/api/redoc")
    OPENAPI_URL: str = env.str("APP_OPENAPI_PATH", "/api/openapi.json")

    # POSTGRES
    POSTGRES_HOST: str = env.str("POSTGRES_HOST")
    POSTGRES_PORT: int = env.int("POSTGRES_PORT", 5432)
    POSTGRES_USER: str = env.str("POSTGRES_USER")
    POSTGRES_PASS: str = env.str("POSTGRES_PASS")
    POSTGRES_DB: str = env.str("POSTGRES_DB")
    POSTGRES_URL: str = env.str(
        "POSTGRES_URL",
        f"postgresql+asyncpg://{env.str('POSTGRES_USER')}:{env.str('POSTGRES_PASS')}@{env.str('POSTGRES_HOST')}:{env.int('POSTGRES_PORT', 5432)}/{env.str('POSTGRES_DB')}"
    )
