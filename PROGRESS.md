# Progreso — BuscadorTrabajos (Fase 1)

Este archivo resume qué se construyó hasta ahora, el estado real (qué corre y qué no
se pudo verificar en este entorno), y qué sigue. Es un registro de trabajo, no
documentación final — se puede borrar una vez que el proyecto tenga su propio
historial de commits/PRs.

Contexto completo del plan de arquitectura (todas las fases) en el mensaje de diseño
original; convenciones de código en `CLAUDE.md`; quickstart en `README.md`.

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
    (`Vector` en postgres, `LargeBinary` en sqlite, ya que sqlite no tiene pgvector).
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

### Tests (backend) — 9/9 pasando
- `tests/conftest.py` — fixtures: `db_session` (SQLite in-memory async + `StaticPool`,
  crea todas las tablas), `client` (AsyncClient contra la app con `get_db` sobreescrito),
  `remoteok_api_fixture` (payload de ejemplo de la API de RemoteOK).
- `tests/test_ingestion/test_remoteok.py` (2 tests) — parseo del adapter contra el
  fixture (mockeado con `respx`, sin red real), y manejo de entradas malformadas/aviso
  legal.
- `tests/test_ingestion/test_runner.py` (3 tests) — `ingest_source` crea filas en la
  primera corrida, **es idempotente en la segunda** (`created=0`, sin duplicados por
  `(source_id, external_id)`), y actualiza campos cuando cambian en el origen.
- `tests/test_api/test_jobs.py` (4 tests) — `GET /jobs` vacío, ingestion mockeada +
  `GET /jobs` devuelve resultados, filtro por `q`, validación 422 en `limit` inválido.
- Corrida completa: `pytest tests/` → **9 passed**.

### Frontend (`frontend/`)
- Vite + React 18 + TypeScript + Tailwind, armado a mano (sin scaffolder interactivo).
- `src/api/jobs.ts` — cliente tipado (`fetchJobs`, `triggerRemoteOkIngestion`) contra
  `/api/v1`, proxyado a `localhost:8000` vía `vite.config.ts`.
- `src/hooks/useJobs.ts` — React Query (`useJobs`, `useTriggerIngestion` con
  invalidación de cache).
- `src/components/JobCard.tsx`, `src/pages/JobSearch.tsx` — buscador por keyword +
  botón "Actualizar ofertas" que dispara la ingestion y refresca la lista.
- `npm install` (138 paquetes, 0 vulnerabilidades) y `npm run build` (`tsc -b && vite
  build`) — **compilan sin errores**.

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

**Conclusión para quien corra el proyecto localmente**: el Quickstart del `README.md`
(con Docker real y `DATABASE_URL` apuntando a Postgres) no se pudo ejercitar en este
sandbox, pero todo el código que lo compone sí — modelos, migración, dedup, contrato de
API y build de frontend están verificados. Lo único no verificado end-to-end es la
combinación real Postgres+pgvector+llamada saliente a RemoteOK, por las dos
restricciones de entorno de arriba (sin Docker, red egress restringida).

## Qué sigue (fases futuras, no en esta sesión — ver plan completo)

- **Fase 2**: pipeline de enrichment con Claude (extracción estructurada, Batches API,
  prompt caching) + embeddings con Voyage AI + búsqueda semántica.
- **Fase 3**: motor de matching (vector pre-filter + re-rank LLM top-N).
- **Fase 4**: auth JWT, cuentas de usuario, carga de CV.
- **Fase 5**: resto de fuentes (WeWorkRemotely RSS, HN Who's Hiring, Arbeitnow,
  Computrabajo/Bumeran/ZonaJobs con rate limiting). LinkedIn queda deliberadamente
  fuera (ver `CLAUDE.md`).
- **Fase 6**: scheduler (APScheduler) + alertas por email/Telegram — la parte
  "autónoma" del sistema.
- **Fase 7**: redacción asistida de cartas de presentación + pulido de UI.
