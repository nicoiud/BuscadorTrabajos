# BuscadorTrabajos

Buscador de empleo inteligente y autónomo: agrega ofertas de múltiples fuentes (APIs
oficiales, RSS y scraping), las normaliza y rankea con IA contra el perfil/CV de cada
usuario, y avisa por email/Telegram cuando aparece algo que matchea — sin postular
automáticamente.

## Estado actual

MVP en construcción por fases (ver plan de arquitectura). Completas: **Fase 1**
(ingestion de RemoteOK, almacenamiento en Postgres, búsqueda por keyword), **Fase 2**
(normalización de avisos + embeddings + búsqueda semántica — tanto el modelo de chat
como el de embeddings son configurables contra cualquier proveedor compatible con la
API de OpenAI (Groq, NVIDIA API Catalog, Ollama local, etc.), ver "Variables de
entorno"), y
un bloque adicional de "asistente de postulación": bandeja de puestos estilo Gmail,
generación de cartas de presentación con IA, y una extensión de navegador (`extension/`)
que completa formularios de postulación en cualquier sitio con tu perfil — nunca los
envía, revisás y postulás vos. Ver `PRIMEROS_PASOS.md` para el detalle de esa parte.
Todavía no hay autenticación, más fuentes, ni scheduler — eso llega en fases
siguientes. Ver `PROGRESS.md` para el detalle de qué se construyó y qué falta.

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

Requisitos: Docker, Python 3.11+, Node 20+.

```bash
# 1. Base de datos (Postgres + pgvector)
docker compose up -d

# 2. Backend
cd backend
cp ../.env.example .env
# completar LLM_API_KEY (Groq o NVIDIA, ver "Variables de entorno" abajo) para que
# el enrichment funcione; para la búsqueda semántica, levantar Ollama local y correr
# `ollama pull mxbai-embed-large` (default de EMBEDDING_* ya apunta ahí)
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --app-dir src

# 3. Traer ofertas reales de RemoteOK (en otra terminal)
curl -X POST http://localhost:8000/api/v1/jobs/ingest/remoteok

# 4. Normalizarlas con IA (título/empresa limpios, seniority, modalidad, salario,
#    resumen, requirements) y generar sus embeddings
curl -X POST http://localhost:8000/api/v1/jobs/enrich

# 5. Buscar por keyword...
curl "http://localhost:8000/api/v1/jobs?q=python"

# ...o por lenguaje natural (requiere que el paso 4 ya haya corrido)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "trabajo remoto de backend en Python, senior", "limit": 10}'

# 6. Frontend
cd ../frontend
npm install
npm run dev
```

Con el frontend corriendo (`http://localhost:5173`), los botones "Actualizar ofertas"
y "Analizar con IA" disparan los pasos 3 y 4 desde la UI, y el toggle
"Palabra clave" / "Búsqueda con IA" alterna entre los pasos 4 y 5.

## Variables de entorno

Ver `.env.example` para la lista completa. Para Fase 1 alcanza con `DATABASE_URL`. A
partir de Fase 2, `POST /jobs/enrich`, `POST /search`, la carta de presentación y el
autofill de la extensión necesitan:

- `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` — cualquier proveedor compatible con la
  API de chat completions de OpenAI. Probado con:
  - **Groq** (gratis): `LLM_BASE_URL=https://api.groq.com/openai/v1`,
    `LLM_MODEL=llama-3.3-70b-versatile`.
  - **NVIDIA API Catalog** (gratis): `LLM_BASE_URL=https://integrate.api.nvidia.com/v1`,
    `LLM_MODEL=meta/llama-3.1-70b-instruct`.
  - No hace falta tocar código para cambiar de uno a otro, solo estas tres variables.
- `EMBEDDING_API_KEY` + `EMBEDDING_BASE_URL` + `EMBEDDING_MODEL` — mismo patrón, para
  los embeddings de la búsqueda semántica. Default: **Ollama local**
  (`EMBEDDING_BASE_URL=http://localhost:11434/v1`, `EMBEDDING_MODEL=mxbai-embed-large`)
  — gratis, corre en tu propia GPU/CPU. Requiere `ollama pull mxbai-embed-large` antes
  de usar "Búsqueda con IA".

Sin `LLM_API_KEY` esos endpoints devuelven error 500 (el resto de la app funciona
igual — ingestion y búsqueda por keyword no dependen de IA). Sin Ollama corriendo (o
sin el modelo de embeddings descargado), "Búsqueda con IA" falla con el mismo tipo de
error — el resto de la app no se ve afectado.

## Tests

```bash
cd backend
pytest
```

Los tests nunca llaman a Groq/NVIDIA/Ollama/RemoteOK reales — todo mockeado (`respx`
para HTTP, stubs para el cliente `openai`, usado tanto para chat como para
embeddings). No hace falta ninguna API key ni tener Ollama corriendo para correr la
suite.

## Extensión de navegador (autofill)

Ver `extension/README.md` para instalarla (`chrome://extensions` → modo desarrollador
→ cargar descomprimida) y probarla. Completa campos de formularios de postulación en
cualquier sitio con tu perfil (guardado local en la extensión) y, para preguntas
abiertas, con una respuesta generada por IA vía `POST /api/v1/autofill/answer`. Nunca
envía el formulario — eso lo hacés vos.
