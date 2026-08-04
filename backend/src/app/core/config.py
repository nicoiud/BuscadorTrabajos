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

    # Embeddings para búsqueda semántica — mismo patrón que LLM_*: cualquier endpoint
    # compatible con la API de embeddings de OpenAI. Default apunta a Ollama local
    # (gratis, sin key real — Ollama no la valida, pero el cliente de OpenAI exige
    # que el campo no esté vacío). mxbai-embed-large genera vectores de 1024
    # dimensiones, igual que EMBEDDING_DIM en job_posting.py — si se cambia de
    # modelo a uno con otra dimensión hace falta una migración.
    embedding_api_key: str = "ollama"
    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_model: str = "mxbai-embed-large"
    enrichment_batch_size: int = 20

    # Empresas a agregar vía las APIs públicas de Greenhouse/Lever (una por
    # cada empresa que use esa plataforma como ATS), separadas por coma. Ej:
    # GREENHOUSE_BOARDS=stripe,notion,airbnb
    # LEVER_COMPANIES=netflix,figma
    # El slug es el que aparece en la URL pública del board de esa empresa
    # (boards.greenhouse.io/<slug> o jobs.lever.co/<slug>).
    greenhouse_boards: str = ""
    lever_companies: str = ""

    # Feeds RSS de We Work Remotely a agregar, separados por coma. Default: solo la
    # categoría de programación (la más relevante para este proyecto) — no se pudo
    # verificar el resto de las URLs de categoría contra el sitio real (sin salida de
    # red en el entorno donde se escribió este adapter), así que se dejan afuera del
    # default en vez de arriesgar URLs rotas. Se pueden agregar más sin tocar código.
    weworkremotely_feed_urls: str = (
        "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    )

    # Remotive (https://remotive.com) — API JSON pública, sin key. Categorías a
    # traer, separadas por coma (una request por categoría). Default: las más
    # relevantes para roles de sistemas/IT.
    remotive_categories: str = "software-dev,devops,qa"

    # Arbeitnow (https://arbeitnow.com) — API JSON pública, sin key, orientada a
    # tech/remoto. No tiene parámetro de categoría; se trae la primera página
    # (100 avisos más recientes) tal cual.

    # Jooble (https://jooble.org/api/about) — agregador con acceso legal a avisos de
    # portales locales (incluye Argentina, a diferencia de Adzuna) vía API key
    # gratuita. Sin key configurada, esta fuente se salta sola (ver
    # `_configured_adapters` en runner.py) — el resto del sistema sigue funcionando
    # igual.
    jooble_api_key: str = ""
    jooble_keywords: str = "sistemas"
    jooble_location: str = "Argentina"

    # Adzuna (https://developer.adzuna.com) — agregador con API gratuita (app_id +
    # app_key). Ojo: Adzuna NO cubre Argentina (países soportados: gb, us, de, fr,
    # nl, ca, au, in, br, pl, za, ru, sg, mx, it, at) — sirve para roles remotos
    # internacionales o de otros países de Latam (mx, br), no para el mercado local.
    # `ADZUNA_COUNTRIES` vacío = fuente deshabilitada (igual que Jooble sin key).
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_countries: str = ""
    adzuna_query: str = "software developer OR programmer OR IT"


settings = Settings()
