from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Agent Service"
    app_env: str = "local"

    # Logging
    log_level: str = "INFO"
    log_model_output: bool = False
    
    # Database
    database_url: str
    
    # Internal service security
    agent_service_token: str | None = None
    allow_dev_user_header: bool = True

    # Provider abstraction
    llm_provider: str = "huggingface"

    # Hugging Face Inference Providers
    hf_token: str | None = None
    hf_base_url: str = "https://router.huggingface.co/v1"
    hf_model: str = "Qwen/Qwen3-32B"

    # LLM generation controls
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2000, ge=256, le=8000)
    llm_timeout_seconds: int = Field(default=60, ge=5, le=300)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()