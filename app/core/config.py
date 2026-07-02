from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://logistics:logistics@localhost:5432/logistics_track"
    redis_url: str = "redis://localhost:6379/0"

    webhook_signing_secret: str = "change-me-in-local-env"
    webhook_max_retries: int = 5
    webhook_timeout_seconds: float = 10.0

    # IA gratuita: normalização via LLM local (Ollama), desligada por padrão.
    llm_normalizer_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    jadlog_api_key: str = ""
    jadlog_api_base_url: str = "https://www.jadlog.com.br/embarcador/tracking"

    polling_interval_seconds: int = 1800
    stalled_shipment_alert_hours: int = 48


@lru_cache
def get_settings() -> Settings:
    return Settings()
