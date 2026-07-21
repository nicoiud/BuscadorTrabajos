# BuscadorTrabajos

Buscador de empleo inteligente y autónomo: agrega ofertas de múltiples fuentes (APIs
oficiales, RSS y scraping), las normaliza y rankea con IA contra el perfil/CV de cada
usuario, y avisa por email/Telegram cuando aparece algo que matchea — sin postular
automáticamente.

## Estado actual

MVP en construcción por fases (ver plan de arquitectura). Fase 1 en curso: ingestion de
una fuente (RemoteOK), almacenamiento en Postgres, y búsqueda básica por API + UI.
Todavía no hay IA, autenticación ni scheduler — eso llega en fases siguientes.

## Arquitectura

```
React (Vite/TS) ──REST/JWT──▶ FastAPI ──▶ Postgres + pgvector
                                 │
                                 ▼
                    APScheduler (in-process)
                    ingestion → enrichment → matching → alerts
                                 │
        ┌────────────────────────┼─────────────────────┐
        ▼                        ▼                      ▼
  APIs oficiales           RSS/agregadores          Scrapers HTML
  (Adzuna, RemoteOK,       (WeWorkRemotely,          (Computrabajo,
   Arbeitnow)               HN Who's Hiring)          Bumeran, ZonaJobs)
```

Ver `CLAUDE.md` para las convenciones del repo y detalle de cada capa.

## Quickstart

Requisitos: Docker, Python 3.12+, Node 20+.

```bash
# 1. Base de datos (Postgres + pgvector)
docker compose up -d

# 2. Backend
cd backend
cp ../.env.example .env   # completar valores si hace falta
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --app-dir src

# 3. Disparar la ingestion de RemoteOK (en otra terminal)
curl -X POST http://localhost:8000/api/v1/jobs/ingest/remoteok

# 4. Ver resultados
curl "http://localhost:8000/api/v1/jobs?q=python"

# 5. Frontend
cd ../frontend
npm install
npm run dev
```

## Variables de entorno

Ver `.env.example` para la lista completa (base de datos, claves de IA, APIs de
fuentes, notificaciones). Solo `DATABASE_URL` es necesaria para la Fase 1.

## Tests

```bash
cd backend
pytest
```
