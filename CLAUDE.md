# CLAUDE.md

Guía para sesiones de Claude Code que trabajen en este repo.

## Qué es esto

Buscador de empleo inteligente y autónomo. Ver `README.md` para el quickstart y el
diagrama de arquitectura. El plan de fases completo (backend, IA, scheduler, frontend)
fue diseñado antes de escribir código; este archivo documenta las convenciones que
deben respetarse a medida que se implementan las fases.

## Convenciones del backend

- Todo acceso a base de datos usa sesiones **async** de SQLAlchemy (`db/session.py`).
  No mezclar clientes sync.
- Los routers en `api/v1/` son delgados: parsean/validan con Pydantic y delegan la
  lógica a `services/`. No poner lógica de negocio ni llamadas a IA directamente en un
  router.
- Cada fuente de ofertas de empleo (API, RSS o scraping) se implementa como un
  `SourceAdapter` en `services/ingestion/` (ver `services/ingestion/base.py`). El
  adapter solo hace I/O y devuelve `RawJobPosting`; nunca escribe campos derivados de
  IA.
- Las llamadas a Claude/Voyage viven exclusivamente en `services/enrichment/` y
  `services/matching/` — nunca inline en un router o en un adapter de ingestion.
- Dedup de ofertas: `(source_id, external_id)` es la clave única en `job_postings`.
  Re-ingestar una oferta ya vista actualiza campos, no crea duplicados.
- Cada fuente tiene un kill-switch (`sources.enabled`) y un `rate_limit_seconds`.
  Cualquier scraper nuevo debe respetar `robots.txt` y usar el `User-Agent` de
  `SCRAPER_USER_AGENT`, nunca simular un browser para evadir bloqueos.

## LinkedIn: explícitamente fuera de alcance

**No agregar un scraper de LinkedIn.** El ToS de LinkedIn prohíbe el scraping y hay
antecedentes de acciones legales (hiQ Labs v. LinkedIn). El modelo de `sources` está
preparado para representar una fuente LinkedIn a futuro, pero solo debería habilitarse
vía la API oficial de partners o carga manual de links por el usuario — no scraping
automatizado. Si una tarea pide "agregar LinkedIn", primero volver a levantar este
riesgo con el usuario en vez de implementarlo directamente.

## Extensión de navegador (`extension/`)

Autofill de formularios de postulación en sitios de terceros, tipo LastPass. Regla
dura, no negociable: **la extensión nunca envía/hace submit de un formulario**. Solo
completa campos para que el usuario revise y postule él mismo — automatizar el submit
es, en la práctica, auto-apply, que fue descartado explícitamente al definir el
alcance del proyecto (ver `PRIMEROS_PASOS.md`). Cualquier cambio a `content.js` debe
preservar esto. El perfil de la extensión vive en `chrome.storage.local` (no en el
backend) hasta que exista Fase 4; usa permisos mínimos (`activeTab`, no `<all_urls>`)
para que el content script solo se inyecte cuando el usuario aprieta el botón, no
automáticamente en cada página.

## Migraciones

Cambios de modelo van siempre acompañados de una migración Alembic
(`alembic revision --autogenerate -m "..."` desde `backend/`, revisar el archivo
generado antes de aplicarlo).

## Scheduler

La parte "autónoma" del sistema vive en `workers/scheduler.py` (APScheduler,
in-process). Los jobs del scheduler llaman funciones de `services/`, nunca
implementan lógica propia — así el mismo código se puede migrar a Celery más
adelante si el volumen lo justifica, sin reescribir la lógica de negocio.

## Testing

- Nunca pegarle a Claude/Voyage ni a sitios externos reales en tests. Mockear HTTP con
  `respx`/`httpx` mock transports y stubear los clientes `anthropic`/`voyageai`.
- Los adapters de ingestion se testean contra fixtures grabados (HTML/JSON guardado),
  no contra el sitio en vivo.

## Cómo correr todo localmente

Ver `README.md` → Quickstart.
