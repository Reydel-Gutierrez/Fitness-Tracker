from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path("/data") if Path("/data").exists() else ROOT_DIR.parent / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Fitness Tracker"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 30
    database_url: str = f"sqlite:///{(DATA_DIR / 'fitness.db').as_posix()}"
    usda_fdc_api_key: str | None = None
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"


@lru_cache
def get_settings() -> Settings:
    return Settings()
