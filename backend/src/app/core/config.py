from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://buscador:buscador@localhost:5432/buscador"

    scraper_user_agent: str = "BuscadorTrabajosBot/0.1 (+contact@example.com)"
    scraper_default_delay_seconds: float = 3.0

    # Cliente de chat/completions compatible con OpenAI. Sirve para Groq
    # (https://api.groq.com/openai/v1), NVIDIA API Catalog
    # (https://integrate.api.nvidia.com/v1), OpenAI mismo, o cualquier otro proveedor
    # que hable el mismo protocolo — solo cambian estas tres variables, no el código.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"

    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"
    enrichment_batch_size: int = 20


settings = Settings()
