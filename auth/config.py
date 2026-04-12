from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """Loads from environment (e.g. JWT_SECRET) and optional `.env` in cwd."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    jwt_secret: str = "dev-only-set-JWT_SECRET-in-production-min-32-characters"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    auth_cookie_name: str = "access_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
