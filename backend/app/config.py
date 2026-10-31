import logging
import secrets
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Determine paths for .env file resolution
_APP_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _APP_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_ROOT_ENV = _PROJECT_ROOT / ".env"
_BACKEND_ENV = _BACKEND_DIR / ".env"

# Secrets that have previously shipped in this repository. They are public, so a
# deployment using one of them lets anyone forge session tokens.
KNOWN_INSECURE_JWT_SECRETS = {
    "super-secret-workout-tracker-token-key-2026-prod",
    "super-secret-workout-tracker-token-key-change-in-prod-2026",
    "changeme",
    "secret",
}

MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    APP_NAME: str = "Workout Tracker"
    # "development" or "production". Production enforces secure defaults.
    ENVIRONMENT: str = "development"

    MONGODB_URI: str = "mongodb://127.0.0.1:27017"
    DATABASE_NAME: str = "workout_tracker"

    # JWT Auth. Must be supplied via environment in production. In development an
    # ephemeral random secret is generated when unset (sessions reset on restart).
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = ""
    GOOGLE_CLIENT_SECRET: Optional[str] = ""
    FRONTEND_URL: str = "http://localhost:8000"

    # Dev / Demo mode allows instant access to a shared demo account.
    # Defaults to off in production unless explicitly enabled.
    ALLOW_DEV_LOGIN: Optional[bool] = None

    # Set to true only when running behind a trusted reverse proxy (e.g. Cloud Run)
    # so the client IP for rate limiting is taken from X-Forwarded-For.
    TRUST_PROXY_HEADERS: bool = False

    # Simple per-instance rate limits (requests per window)
    AUTH_RATE_LIMIT: int = 10
    AUTH_RATE_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=(".env", str(_BACKEND_ENV), str(_ROOT_ENV)),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("prod", "production")

    @property
    def cookie_secure(self) -> bool:
        return self.FRONTEND_URL.lower().startswith("https://")

    @property
    def allowed_origins(self) -> List[str]:
        origins = [self.FRONTEND_URL.rstrip("/")]
        if not self.is_production:
            origins += [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ]
        return list(dict.fromkeys(origins))

    @model_validator(mode="after")
    def _enforce_secure_defaults(self) -> "Settings":
        secret = (self.JWT_SECRET or "").strip()
        insecure = (
            not secret
            or secret in KNOWN_INSECURE_JWT_SECRETS
            or len(secret) < MIN_JWT_SECRET_LENGTH
        )

        if self.is_production:
            if insecure:
                raise ValueError(
                    "JWT_SECRET must be set to a random value of at least "
                    f"{MIN_JWT_SECRET_LENGTH} characters in production "
                    "(e.g. `python -c 'import secrets; print(secrets.token_urlsafe(48))'`)."
                )
            if self.ALLOW_DEV_LOGIN is None:
                self.ALLOW_DEV_LOGIN = False
        else:
            if not secret:
                self.JWT_SECRET = secrets.token_urlsafe(48)
                logger.warning(
                    "JWT_SECRET is not set; generated an ephemeral development secret. "
                    "Sessions will not survive a restart."
                )
            elif insecure:
                logger.warning("JWT_SECRET is weak or publicly known. Never use it in production.")
            if self.ALLOW_DEV_LOGIN is None:
                self.ALLOW_DEV_LOGIN = True

        if self.ALLOW_DEV_LOGIN and self.is_production:
            logger.warning(
                "ALLOW_DEV_LOGIN is enabled in production: anyone can sign in to the shared demo account."
            )
        return self


def redact_uri(uri: str) -> str:
    """Removes credentials from a connection URI so it is safe to log."""
    try:
        parts = urlsplit(uri)
        if parts.password or parts.username:
            host = parts.hostname or ""
            if parts.port:
                host = f"{host}:{parts.port}"
            return urlunsplit((parts.scheme, f"***:***@{host}", parts.path, "", ""))
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except Exception:
        return "<redacted>"


settings = Settings()
