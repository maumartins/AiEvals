"""Configurações da aplicação via variáveis de ambiente."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "AI Response Quality Lab"
    debug: bool = False
    app_secret_key: str = "dev-secret-key"

    # Provider padrão
    default_provider: str = "mock"
    openai_api_key: str = ""
    openai_default_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_default_model: str = "claude-3-5-haiku-20241022"

    # Judge
    judge_provider: str = "mock"
    judge_model: str = "mock"

    # Banco
    database_url: str = "sqlite:///./data/aievals.db"

    # Observabilidade
    log_level: str = "INFO"
    otel_enabled: bool = False


settings = Settings()
