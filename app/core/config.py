from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "QueueLens"
    app_env: str = "development"

    database_url: str
    redis_url: str

    celery_broker_url: str
    celery_result_backend: str

    ingestion_api_url: str = "http://127.0.0.1:8000/api/v1/events/batch"
    event_batch_size: int = 100
    event_sender_timeout: float = 5.0
    event_flush_interval: float = 5.0
    queuelens_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
