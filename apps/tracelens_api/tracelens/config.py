from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "local"
    database_url: str = "postgresql+psycopg://tracelens:tracelens@postgres:5432/tracelens"
    redis_url: str = "redis://redis:6379/0"
    prometheus_url: str = "http://prometheus:9090"
    tempo_url: str = "http://tempo:3200"
    loki_url: str = "http://loki:3100"
    analysis_interval_seconds: int = 10
    incident_correlation_window_seconds: int = 180
    simulator_enabled: bool = True
    ai_provider: str = "disabled"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
