# Progreso — BuscadorTrabajos (Fase 1 + Fase 2)

Este archivo resume qué se construyó hasta ahora, el estado real (qué corre y qué no
se pudo verificar en este entorno), y qué sigue. Es un registro de trabajo, no
documentación final — se puede borrar una vez que el proyecto tenga su propio
historial de commits/PRs.

Contexto completo del plan de arquitectura (todas las fases) en el mensaje de diseño
original; convenciones de código en `CLAUDE.md`; quickstart en `README.md`.

> **Actualización posterior**: todo lo que este archivo describe abajo como "Claude"/
> "Anthropic" se implementó originalmente contra la API de Anthropic, pero luego se
> migró a un cliente genérico compatible con OpenAI (`services/enrichment/
> llm_client.py`) para poder usar Groq o NVIDIA API Catalog (gratuitos) en vez de
> Anthropic — ver `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL` en `.env.example` y el
> registro correspondiente en `PRIMEROS_PASOS.md`. El resto de las decisiones
> (tool-calling forzado, batching, etc.) sigue vigente, solo cambió el proveedor.
>
> **Bug encontrado al correr contra Postgres real** (justo el tipo de cosa que este
> archivo advertía que podía pasar sin Postgres disponible para probar en el sandbox):
> los modelos con columnas `Enum(...)` mandaban el `.name` de los enums de Python
> (`"PENDING"`, mayúscula) en vez del `.value` (`"pending"`, como los creó la
> migración) — rompía con `invalid input value for enum`. En SQLite no se notaba
> porque los tests crean el schema con `Base.metadata.create_all()`, que genera su
> propio CHECK constraint a partir del mismo código que hace el INSERT, así que ambos
> lados coincidían por construcción. Fix: `values_callable=lambda obj: [e.value for e
> in obj]` en cada `Enum(...)` de `models/job_posting.py` y `models/source.py`
> (encapsulado en un helper `_enum()` en cada archivo). Verificado con
> `bind_processor()` del dialecto de Postgres directamente (sin Postgres corriendo en
> este sandbox), y confirmado por el usuario corriendo `POST /jobs/ingest/remoteok`
> contra su Postgres real (trajo 100 ofertas).
>
> **Segundo bug encontrado, este con datos reales de Groq**: al correr
> `POST /jobs/enrich` contra los 100 avisos reales de RemoteOK, algunos avisos no
> traen info suficiente para inferir `seniority`/`modality`, y el modelo a veces
> respondía `null` o hasta la palabra `"null"` como texto para esos campos —
> requeridos en nuestro schema, así que Groq rechazaba la tool call entera con 400.
> Como `llm_client.call_with_tool` no atrapaba errores de la librería `openai`, ese
> 400 se propagaba sin filtrar hasta el endpoint y **tiraba abajo todo el lote** (los
> 20 avisos del batch) en vez de marcar solo ese aviso como `failed` y seguir. Fix en
> dos partes: (1) `llm_client.py` ahora atrapa `openai.OpenAIError` y lo traduce a
> `LLMError`, que `extractor.py`/`cover_letter.py` ya traducían a su vez a su propia
> excepción — así el `except` que ya existía en `pipeline.py` por-aviso vuelve a
> funcionar como se pensó; (2) `seniority`/`modality` pasaron a ser opcionales en el
> schema y en `JobExtraction` (se instruye al modelo a omitirlos en vez de inventar o
> mandar la palabra "null"), reduciendo cuántos avisos disparan el error en primer
> lugar. 3 tests nuevos cubren esto — incluido uno que reproduce el escenario exacto
> (un aviso falla, el siguiente en el mismo lote se procesa igual). 31/31 tests.
> Falta que el usuario confirme que `POST /jobs/enrich` ya no crashea contra los 100
> avisos reales con este fix.

## Ya creado

### Scaffolding raíz
- `README.md` — quickstart y diagrama de arquitectura.
- `CLAUDE.md` — convenciones para futuras sesiones (async SQLAlchemy, `SourceAdapter`,
  dónde van las llamadas a IA, dedup, kill-switch por fuente, **LinkedIn explícitamente
  fuera de alcance**, migraciones, scheduler, testing).
- `.env.example`, `.gitignore`, `docker-compose.yml` (Postgres con `pgvector/pgvector:pg16`).

### Backend (`backend/`)
- `pyproject.toml` con dependencias mínimas para Fase 1 (FastAPI, SQLAlchemy async,
  asyncpg, alembic, pydantic-settings, httpx, pgvector; dev: pytest, pytest-asyncio,
  respx, aiosqlite, ruff).
- `src/app/core/config.py` (settings vía pydantic-settings), `core/logging.py`.
- `src/app/db/base.py`, `db/session.py` (engine/sesión async).
- **Modelos** (`src/app/models/`):
  - `source.py` — `Source` (slug, type api/rss/scrape, region, language, enabled,
    rate_limit_seconds, last_run_at/last_success_at, config JSON).
  - `job_posting.py` — `JobPosting` con campos raw (title/company/description/location,
    posted_at, scraped_at, language, region) + campos IA nullable (title_normalized,
    seniority, modality, salary, requirements, summary, `embedding vector(1024)`,
    enrichment_status/model). Unique `(source_id, external_id)` para dedup.
  - Tipos elegidos cross-dialect (`sa.Uuid`, `sa.JSON` con variante `JSONB` en
    postgres) para que el mismo modelo sirva en tests con SQLite y en producción con
    Postgres+pgvector; el único tipo con variante especial es `embedding`
    (`Vector` en postgres, `JSON` en sqlite — sqlite no tiene pgvector, pero así los
    tests igual pueden persistir y leer el `list[float]` real, no solo mockearlo).
- **Alembic**: `alembic.ini`, `alembic/env.py` (async, lee `DATABASE_URL` de settings),
  migración inicial `alembic/versions/0001_initial_schema.py` (crea extensión
  `vector`, tablas `sources` y `job_postings` con sus enums). Escrita a mano porque no
  hay Postgres disponible en este sandbox para correr `--autogenerate` en vivo;
  verificada con `alembic history` (carga sin errores) y con `Base.metadata` (los
  modelos registran las mismas tablas).
- **Ingestion** (`src/app/services/ingestion/`):
  - `base.py` — interfaz `SourceAdapter.fetch() -> list[RawJobPosting]` (dataclass
    `RawJobPosting`, solo I/O, sin campos de IA).
  - `remoteok.py` — adapter de la API pública de RemoteOK (sin API key), primera
    fuente elegida por fricción cero. Filtra el aviso legal que devuelve el endpoint,
    parsea fecha ISO con manejo de errores.
  - `runner.py` — `ingest_source(db, adapter)`: crea/reusa el `Source`, hace upsert de
    `JobPosting` por `(source_id, external_id)` (dedup real, no duplica filas en
    re-ingestas), actualiza `last_run_at`/`last_success_at`, devuelve `IngestResult`
    (fetched/created/updated).
- **API** (`src/app/api/v1/jobs.py` + `schemas/job.py`):
  - `GET /api/v1/jobs` — filtros por `q` (keyword sobre title/description), `region`,
    `language`, paginación (`limit`/`offset`), solo activos, ordenado por fecha.
  - `POST /api/v1/jobs/ingest/remoteok` — dispara la ingestion manualmente.
  - `main.py` — app factory, CORS habilitado para `localhost:5173` (frontend Vite),
    `GET /health`.
- Verificado con imports reales (venv creado, deps instaladas, `alembic history` OK,
  `app.openapi()` muestra las 3 rutas registradas correctamente).

### Pipeline de IA — Fase 2 (`src/app/services/enrichment/`, `services/search/`)
- `core/config.py` — `anthropic_api_key`, `voyage_api_key`, `claude_model`
  (`claude-sonnet-5`), `voyage_model` (`voyage-3`), `enrichment_batch_size`.
- `enrichment/extractor.py` — `extract_job_fields(title, company, description)` llama
  a Claude **forzando un tool call** (`tool_choice`) con un JSON schema de
  `record_job_extraction` (title_normalized, company_normalized, seniority, modality,
  salary_min/max, currency, requirements, summary). Se eligió tool-use en vez de pedir
  JSON en texto libre porque el schema queda validado por el propio modelo, no por un
  parser frágil después. `get_client()` es una función separada (no un cliente global)
  para poder mockearla fácil en tests sin tocar variables de entorno.
- `enrichment/embeddings.py` — `embed_documents()` (batch, `input_type="document"`)
  para avisos y `embed_query()` (`input_type="query"`) para búsquedas — Voyage separa
  ambos modos porque el embedding de una query corta y el de un documento largo no son
  simétricos.
- `enrichment/pipeline.py` — `enrich_pending_jobs(db, limit)`: toma hasta `limit` avisos
  con `enrichment_status=pending`, extrae campos con Claude, y **solo si la extracción
  fue exitosa** arma el batch de embeddings (un solo call a Voyage para todos los
  avisos del lote, no uno por aviso). Si `extract_job_fields` tira `ExtractionError`
  para un aviso puntual, ese aviso queda `enrichment_status=failed` y el resto del lote
  sigue procesándose — un aviso raro no rompe el batch entero.
- `services/search/semantic.py` — `semantic_search(db, query_embedding, limit)` usa
  `JobPosting.embedding.cosine_distance(...)` (pgvector) para rankear; solo considera
  avisos `is_active` y `enrichment_status=done` (no tiene sentido rankear por embedding
  algo que todavía no tiene uno).
- **API**: `POST /jobs/enrich` (dispara el pipeline manualmente, `limit` opcional) y
  `POST /search` (body `{query, limit}`, embebe la query y devuelve avisos rankeados).
  Registrados en `main.py`.
- Decisión consciente vs. el plan original: para tener un MVP demostrable hoy se usa la
  **Messages API síncrona** en batches chicos (no la Batches API async al 50% de costo
  que menciona el plan de arquitectura) — queda anotado como optimización de costo
  pendiente para cuando el volumen lo justifique, no es una limitación técnica.

### Tests (backend) — 20/20 pasando
- `tests/conftest.py` — fixtures: `db_session` (SQLite in-memory async + `StaticPool`,
  crea todas las tablas), `client` (AsyncClient contra la app con `get_db` sobreescrito),
  `remoteok_api_fixture` (payload de ejemplo de la API de RemoteOK).
- `tests/test_ingestion/test_remoteok.py` (2 tests) — parseo del adapter contra el
  fixture (mockeado con `respx`, sin red real), y manejo de entradas malformadas/aviso
  legal.
- `tests/test_ingestion/test_runner.py` (3 tests) — `ingest_source` crea filas en la
  primera corrida, **es idempotente en la segunda** (`created=0`, sin duplicados por
  `(source_id, external_id)`), y actualiza campos cuando cambian en el origen.
- `tests/test_api/test_jobs.py` (5 tests) — `GET /jobs` vacío, ingestion mockeada +
  `GET /jobs` devuelve resultados, filtro por `q`, validación 422 en `limit` inválido,
  y `POST /jobs/enrich` con el pipeline mockeado.
- `tests/test_api/test_search.py` (1 test) — `POST /search` con `embed_query` y
  `semantic_search` mockeados, verifica que la query se embebe y el resultado se
  serializa bien.
- `tests/test_services/test_extractor.py` (3 tests) — parseo de la respuesta tool-use
  de Claude (mock de `AsyncAnthropic`, sin red real), y dos casos de error
  (`ExtractionError` cuando no hay tool_use block o falta un campo requerido).
- `tests/test_services/test_embeddings.py` (3 tests) — `embed_documents`/`embed_query`
  contra un fake client de Voyage, y que una lista vacía no dispara ningún call a la API.
- `tests/test_services/test_enrichment_pipeline.py` (3 tests) — pipeline completo
  contra sqlite real: enrichment exitoso persiste campos + embedding, extracción fallida
  marca `failed` sin tocar embeddings, y no-op cuando no hay nada pendiente.
- Corrida completa: `pytest tests/` → **20 passed**.

### Frontend (`frontend/`)
- Vite + React 18 + TypeScript + Tailwind, armado a mano (sin scaffolder interactivo).
- `src/api/jobs.ts` — cliente tipado (`fetchJobs`, `semanticSearchJobs`,
  `triggerRemoteOkIngestion`, `triggerEnrichment`) contra `/api/v1`, proxyado a
  `localhost:8000` vía `vite.config.ts`.
- `src/hooks/useJobs.ts` — React Query (`useJobs` con modo `keyword`/`semantic`,
  `useTriggerIngestion`, `useTriggerEnrichment`, ambos invalidan la cache de jobs).
- `src/components/JobCard.tsx` — ahora muestra seniority/modalidad/salario/resumen/
  requirements cuando el aviso ya fue enriquecido (`enrichment_status === "done"`);
  si no, se ve igual que en Fase 1 (título/empresa crudos).
- `src/pages/JobSearch.tsx` — toggle "Palabra clave" / "Búsqueda con IA", botón
  "Analizar con IA" (dispara `POST /jobs/enrich`) al lado de "Actualizar ofertas".
- `npm install` y `npm run build` (`tsc -b && vite build`) — **compilan sin errores**
  después de los cambios de Fase 2.

## Verificación end-to-end — qué se pudo probar en este sandbox y qué no

Sin Docker disponible (`docker compose up` falla: no existe el socket del daemon;
`service docker start` falla por restricción de `ulimit`), la verificación se adaptó
así:

- **Migración inicial**: escrita a mano (no autogenerada) porque no hay Postgres real
  para compararle el schema. Validada con `alembic history` (carga sin errores) y con
  `Base.metadata` (los modelos registran las mismas tablas que crea la migración).
- **App real corriendo**: se levantó `uvicorn` en este sandbox contra una base SQLite
  local (creada con `Base.metadata.create_all`, no vía Alembic — Alembic requiere
  Postgres por el `CREATE EXTENSION vector`). `GET /health` y `GET /api/v1/jobs`
  respondieron correctamente contra un servidor real, no mockeado.
- **Ingestion real contra RemoteOK**: **bloqueada por la política de red del sandbox**,
  no por un bug de código. El proxy de salida rechaza la conexión a `remoteok.com` con
  `403 Forbidden` (`gateway answered 403 to CONNECT — policy denial`, confirmado en
  `$HTTPS_PROXY/__agentproxy/status`). El código del adapter está probado contra el
  contrato HTTP real de RemoteOK vía fixtures/`respx` (mismo JSON, misma forma), pero
  no se pudo hacer la llamada saliente real desde este entorno.
- El servidor de prueba y el archivo SQLite temporal se detuvieron/borraron al
  terminar — no quedan artefactos de este smoke test en el repo.
- **Fase 2, mismo smoke test**: con el server sqlite arriba, `POST /jobs/enrich` sin
  avisos pendientes respondió `{"processed":0,"enriched":0,"failed":0}` real (no
  mockeado). `POST /search` devolvió `500` porque `VOYAGE_API_KEY` está vacía en este
  sandbox — **es el comportamiento esperado sin la key**, no un bug; se confirmó que el
  server siguió vivo después del error (`GET /health` respondió `ok` inmediatamente
  después).

**Conclusión para quien corra el proyecto localmente**: el Quickstart del `README.md`
(con Docker real, `DATABASE_URL` apuntando a Postgres, y `ANTHROPIC_API_KEY`/
`VOYAGE_API_KEY` cargadas) no se pudo ejercitar completo en este sandbox, pero todo el
código que lo compone sí — modelos, migración, dedup, pipeline de enrichment, contrato
de API y build de frontend están verificados con tests + un server real corriendo. Lo
único no verificado end-to-end con datos reales es: (1) Postgres+pgvector real (acá se
usó sqlite), (2) la llamada saliente a RemoteOK (red del sandbox la bloquea), y (3) las
llamadas reales a Claude/Voyage (no hay API keys en este sandbox). Los tres son
limitaciones del entorno de esta sesión, no del código — para tenerlo funcionando esta
noche con datos e IA reales:

1. `docker compose up -d`
2. En `backend/.env`: completar `ANTHROPIC_API_KEY` y `VOYAGE_API_KEY` (las otras
   variables ya tienen default razonable).
3. `alembic upgrade head` (acá sí corre contra Postgres real, con pgvector).
4. Levantar backend + frontend, `POST /jobs/ingest/remoteok`, `POST /jobs/enrich`, y
   probar tanto la búsqueda por keyword como la de IA — todo el flujo detallado en el
   Quickstart del `README.md`.

## Qué sigue (fases futuras — ver plan completo)

- **Fase 3**: motor de matching CV↔oferta (vector pre-filter + re-rank LLM top-N). Sin
  `profiles`/`users` todavía no hay CV real contra el cual matchear — se puede
  adelantar el scoring contra un perfil demo hardcodeado antes de tener auth.
- **Fase 4**: auth JWT, cuentas de usuario, carga de CV.
- **Fase 5**: resto de fuentes (WeWorkRemotely RSS, HN Who's Hiring, Arbeitnow,
  Computrabajo/Bumeran/ZonaJobs con rate limiting). LinkedIn queda deliberadamente
  fuera (ver `CLAUDE.md`).
- **Fase 6**: scheduler (APScheduler) + alertas por email/Telegram — la parte
  "autónoma" del sistema.
- **Fase 7**: redacción asistida de cartas de presentación + pulido de UI.
- **Optimización de costo pendiente de Fase 2**: migrar `enrich_pending_jobs` de la
  Messages API síncrona a la Batches API (50% más barato, asíncrono) cuando el volumen
  de avisos lo justifique — hoy se priorizó velocidad de entrega sobre costo.
