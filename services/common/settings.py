from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    service_name: str
    service_version: str = "0.1.0"
    environment: str = "local"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4318"
    simulator_enabled: bool = True
    nats_url: str = "nats://nats:4222"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> ServiceSettings:
    return ServiceSettings()  # type: ignore[call-arg]
