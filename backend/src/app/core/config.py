from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://buscador:buscador@localhost:5432/buscador"

    scraper_user_agent: str = "BuscadorTrabajosBot/0.1 (+contact@example.com)"
    scraper_default_delay_seconds: float = 3.0


settings = Settings()
