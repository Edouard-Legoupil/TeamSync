"""Application configuration.

All settings are read from environment variables (or a local ``.env`` file).
See ``.env.example`` for the full list.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Database -----------------------------------------------------------
    # PostgreSQL is the production default. SQLite works out of the box for
    # local development: sqlite:///./teamsync.db
    DATABASE_URL: str = "sqlite:///./teamsync.db"

    # --- Azure AD SSO -------------------------------------------------------
    AZURE_AD_TENANT_ID: str = ""
    AZURE_AD_CLIENT_ID: str = ""
    AZURE_AD_CLIENT_SECRET: str = ""
    # Must match the redirect URI registered in the Azure AD app registration.
    AZURE_AD_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"

    # --- Application JWT -----------------------------------------------------
    JWT_SECRET_KEY: str = "dev-only-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # --- AI pipeline ---------------------------------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Azure OpenAI (optional alternative to plain OpenAI):
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"

    # --- App / frontend ------------------------------------------------------
    # Origin that serves the SPA. Used for CORS and post-login redirects.
    FRONTEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8000"
    # Absolute or relative path to the built frontend (frontend/dist).
    STATIC_DIR: str = "../frontend/dist"

    # --- Developer conveniences ---------------------------------------------
    # When true, exposes GET /api/auth/dev-login?email=... for local testing
    # without Azure AD. MUST be false in production.
    ALLOW_DEV_LOGIN: bool = False
    # Email used by the dev-login redirect when Azure AD is not configured.
    DEV_LOGIN_EMAIL: str = "supervisor@example.org"

    # Microsoft Graph (Outlook) server-side integration. Off by default because
    # it requires an app registration with Mail.Send / Calendars.ReadWrite and
    # admin consent. The .ics export and Outlook Web deeplinks work without it.
    MICROSOFT_GRAPH_ENABLED: bool = False
    # Timezone used to compute "overdue"/"due soon" in the field context.
    # Per-user timezones are a future step; this is the organisation default.
    APP_TIMEZONE: str = "UTC"
    # Simple in-process rate limit (requests per client IP per minute).
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def cookie_secure(self) -> bool:
        return self.FRONTEND_URL.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
