import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Determine paths for .env file resolution
_APP_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _APP_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_ROOT_ENV = _PROJECT_ROOT / ".env"
_BACKEND_ENV = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Workout Tracker"
    MONGODB_URI: str = "mongodb://127.0.0.1:27017"
    DATABASE_NAME: str = "workout_tracker"
    
    # JWT Auth
    JWT_SECRET: str = "super-secret-workout-tracker-token-key-2026-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = ""
    GOOGLE_CLIENT_SECRET: Optional[str] = ""
    FRONTEND_URL: str = "http://localhost:8000"
    
    # Dev / Demo mode allows instant access if Google credentials are not yet configured
    ALLOW_DEV_LOGIN: bool = True

    model_config = SettingsConfigDict(
        env_file=(".env", str(_BACKEND_ENV), str(_ROOT_ENV)),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
