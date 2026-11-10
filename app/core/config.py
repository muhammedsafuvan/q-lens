from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "QueueLens"
    app_env: str = "development"

    database_url: str
    queuelens_api_key: str

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8001/api/v1/auth/google/callback"

    session_secret_key: str | None = None
    frontend_url: str = "http://localhost:3000"

    jwt_secret_key: str | None = None
    jwt_access_token_minutes: int = 15
    refresh_token_days: int = 30

    jwt_issuer: str = "queuelens-api"
    jwt_audience: str = "queuelens-dashboard"


@lru_cache
def get_settings() -> Settings:
    return Settings()
