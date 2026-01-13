"""WhatsApp Agent configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str

    # OpenRouter LLM
    openrouter_api_key: str
    openrouter_model: str = "openai/gpt-5.2"

    # Evolution API
    evolution_api_url: str
    evolution_api_key: str
    evolution_instance: str

    # Agent behavior
    debounce_seconds: int = 10


settings = Settings()
