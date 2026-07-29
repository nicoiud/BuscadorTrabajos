# Primeros pasos — BuscadorTrabajos

Registro de por dónde vamos y qué sigue. Es el punto de entrada para retomar la
conversación en una sesión nueva — para el detalle técnico de lo ya construido
(archivos, tests, decisiones de arquitectura) ver `PROGRESS.md`; para las
convenciones del repo, `CLAUDE.md`; para correrlo, `README.md`.

## Dónde estamos

**Fase 1 y Fase 2 construidas, testeadas (20/20 tests) y pusheadas** a
`claude/smart-job-search-bn64tr`:

- Backend FastAPI + Postgres/pgvector, frontend React.
- Ingestion de RemoteOK con dedup real.
- Pipeline de IA: normalización de avisos con Claude (título/empresa/seniority/
  modalidad/salario/requirements/resumen) + embeddings con Voyage AI + búsqueda
  semántica en lenguaje natural.
- Todavía **no hay cuentas de usuario** (Fase 4), **no hay más fuentes** que RemoteOK
  (Fase 5), y **no hay scheduler/alertas automáticas** (Fase 6) — todo se dispara
  manualmente hoy (botones en la UI o `curl`).

Para probarlo en tu máquina (necesita Docker, que no tengo en este sandbox): ver
"Quickstart" en `README.md`.

## Lo nuevo que estamos definiendo (todavía sin construir)

Surgió un pedido nuevo que no estaba en el plan original: una forma de revisar los
puestos encontrados y agilizar la postulación. Fuimos afinando el alcance en la
conversación porque la primera lectura ("que rellene el formulario del sitio original
solo") es riesgosa, y terminamos en una versión distinta y segura:

1. **Bandeja de entrada estilo Gmail** — pantalla nueva en el frontend que lista todos
   los puestos encontrados, con detalle al hacer click y la posibilidad de ir
   marcando/seleccionando los que interesan. Esto es una vista nueva sobre datos que
   ya tenemos (`job_postings`), no necesita nada de infraestructura nueva.

2. **Asistente de postulación con IA** — por cada puesto seleccionado, generar
   automáticamente un borrador de carta de presentación + respuestas típicas
   (por qué te interesa, pretensión salarial, etc.) usando el CV/perfil del usuario +
   el aviso. El usuario copia/pega eso donde postule. Esto es esencialmente la
   Fase 7 del plan original ("redacción asistida"), adelantada.

3. **Extensión de navegador tipo LastPass** — el pedido de "que detecte lo que pide el
   formulario y lo rellene con mi información". Confirmado como viable
   técnicamente: una extensión puede inyectar un *content script* en la página que
   estés mirando (LinkedIn, Computrabajo, el sitio que sea) con permiso del navegador
   para leer y escribir el DOM de esa página — es el mismo mecanismo que usan LastPass,
   1Password, el autocompletado nativo de Chrome, etc. Completa los campos
   (nombre/email/teléfono/etc., y para preguntas de texto libre puede usar el borrador
   generado por la IA del punto 2) pero **nunca aprieta "enviar"** — el usuario revisa
   y postula él mismo.

### Regla dura, no negociable

**Nunca automatizar el submit/envío de un formulario de terceros.** Esto fue
explícitamente descartado al arrancar el proyecto (se eligió "búsqueda + alertas" y
se descartó "auto-apply" por el riesgo de ToS, fragilidad y necesidad de guardar
credenciales de sitios ajenos). Completar campos para que el usuario revise y mande él
mismo está bien; que el sistema decida y postule solo, no. Si alguna tarea futura pide
acercarse a eso, hay que volver a levantar el tema antes de implementarlo, igual que ya
dice `CLAUDE.md` para LinkedIn.

### Decisión de scope tomada

Para tener esto funcionando rápido, **el perfil que usa la extensión para rellenar
vive local en la extensión misma** (el usuario lo carga una vez en una pantalla de
opciones), en vez de depender de que exista Fase 4 (cuentas de usuario en el backend).
Esto evita bloquear la extensión en construir auth primero. Más adelante se puede
migrar a un perfil sincronizado con el backend una vez que Fase 4 exista.

## Qué sigue (próximos pasos concretos, en orden)

1. ✅ **Hecho** — Bandeja tipo Gmail en el frontend. `pages/JobInbox.tsx` (reemplazó
   `JobSearch.tsx`, borrado) con layout de dos paneles: `components/JobListRow.tsx`
   (fila estilo email, con checkbox de selección) a la izquierda,
   `components/JobDetailPanel.tsx` (detalle completo + link al aviso original) a la
   derecha. Selección persistida en `localStorage` vía `hooks/useSelectedJobs.ts`
   (sobrevive a recargar la página — verificado con Playwright, no solo en memoria).
   En mobile el detalle se abre a pantalla completa con botón "← Volver". Verificado
   visualmente con Playwright contra datos de prueba (sqlite local, no había Postgres
   real en este sandbox): navegación lista→detalle, toggle de selección, cambio de
   modo palabra clave/IA, y persistencia tras reload — todo funcionando. Build y 20
   tests de backend siguen pasando.
2. ✅ **Hecho** — Asistente de carta de presentación con IA por puesto.
   `services/enrichment/cover_letter.py` (mismo patrón tool-use que el extractor de
   Fase 2) genera `{cover_letter, key_points}` con Claude a partir del aviso + el
   perfil del usuario. Endpoint `POST /jobs/{job_id}/cover-letter` (404 si el puesto no
   existe). El perfil del usuario **vive en `localStorage`** (`hooks/useProfile.ts`,
   textarea "Mi perfil" en el header de la bandeja) — mismo criterio que la selección
   de puestos, sin depender de Fase 4. En el detalle de cada puesto,
   `components/CoverLetterAssistant.tsx` tiene el botón "Generar carta con IA"
   (deshabilitado hasta completar el perfil), muestra el borrador en un textarea con
   botón "Copiar" (clipboard), y los puntos clave reusables. 5 tests nuevos (25/25
   backend). Verificado end-to-end con Playwright contra un backend con Claude
   mockeado (no hay `ANTHROPIC_API_KEY` real en este sandbox): cargar perfil → abrir
   puesto → generar carta → se renderiza el borrador — funcionó completo.
3. ✅ **Hecho** — Extensión de navegador (`extension/`, Manifest V3, nuevo componente
   del repo). `options.html`/`options.js` guardan un perfil estructurado (nombre,
   apellido, email, teléfono, LinkedIn, portfolio, ubicación, años de experiencia,
   resumen/CV) en `chrome.storage.local` — perfil propio de la extensión, separado del
   `localStorage` de la web app (son orígenes distintos, no pueden compartir storage).
   `content.js` (inyectado solo al apretar el botón del popup, vía `activeTab` +
   `scripting` — nunca corre solo en cada página que visitás) recorre `input`/
   `textarea` visibles, matchea por label/placeholder/name contra un diccionario de
   heurísticas (email, teléfono, LinkedIn, nombre/apellido, ubicación, años de
   experiencia) y completa directo. Para `textarea` que parecen preguntas abiertas
   (terminan en "?", "por qué", "cuéntanos", etc.) pide una respuesta a
   `POST /api/v1/autofill/answer` (nuevo endpoint, `services/enrichment/
   field_answer.py`, mismo patrón Claude que el resto) — como máximo 5 por formulario.
   `background.js` hace el fetch real (el content script no puede por CORS/CSP de la
   página de terceros), usando `host_permissions` para `localhost:8000` por default, y
   pidiendo permiso dinámico (`chrome.permissions.request`) si se cambia a otra URL de
   API en Opciones. **Nunca toca el botón de submit** — regla dura respetada.
   28/28 tests backend. Verificado end-to-end con Playwright cargando la extensión de
   verdad en Chromium (`launch_persistent_context` con `--load-extension`) contra un
   formulario de prueba y el backend con Claude mockeado: perfil guardado → click en
   "Rellenar este formulario" → los 6 campos se completaron correctamente (incluida la
   respuesta de IA a "¿Por qué te interesa este puesto?") → el botón "Enviar
   postulación" quedó intacto, sin tocar. Nota: para que `chrome.tabs.query` pudiera
   ubicar la pestaña de prueba en el entorno de test se usó una copia temporal de la
   extensión con permisos ampliados (`tabs` + host_permissions extra) — la extensión
   commiteada en el repo mantiene los permisos mínimos (`activeTab`, sin `tabs`, sin
   `<all_urls>`) que es como se usa en la vida real (el click en el ícono de la
   extensión ya le da acceso temporal a la pestaña activa).
4. (Más adelante, no bloqueante) migrar el perfil de la extensión a estar sincronizado
   con el backend cuando exista Fase 4, en vez de vivir solo local.

Los tres pasos del plan de autofill están completos. Ver `extension/README.md` para
cómo cargarla y probarla.

## Cambio de proveedor de IA: Anthropic → Groq/NVIDIA (configurable)

El usuario no quería depender de la API paga de Anthropic y tiene acceso gratuito a
Groq y a NVIDIA API Catalog — ambos exponen una API de chat compatible con el formato
de OpenAI (mismo shape de `tools`/`tool_choice`/`chat.completions.create`). En vez de
elegir uno solo, se armó un cliente genérico:

- `services/enrichment/llm_client.py` — `get_client()` devuelve un `openai.AsyncOpenAI`
  apuntado a `settings.llm_base_url` con `settings.llm_api_key`; `call_with_tool(...)`
  (usado por `extractor.py` y `cover_letter.py`, fuerza una function call y devuelve
  los argumentos ya parseados) y `call_text(...)` (usado por `field_answer.py`,
  respuesta de texto libre).
- `core/config.py` — `llm_api_key` / `llm_base_url` / `llm_model` reemplazan a
  `anthropic_api_key`/`claude_model`. Cambiar de Groq a NVIDIA (o a cualquier otro
  proveedor compatible) es solo cambiar estas tres variables en `.env`, sin tocar
  código. Voyage AI se mantiene sin cambios para los embeddings (decisión: no se pidió
  reemplazar esa parte, solo el chat/completions).
- Se sacó la dependencia `anthropic` de `pyproject.toml`, se agregó `openai`.
- Tests: los fakes de `AsyncAnthropic` (`FakeToolUseBlock`, etc.) se reemplazaron por
  fakes con la forma de respuesta de OpenAI (`choices[0].message.tool_calls` /
  `.content`), centralizados en `conftest.py` (`patch_llm`, `tool_call_response`,
  `text_response`, `empty_response`) para no triplicar el boilerplate en los tres
  archivos de test que los usan. 28/28 tests siguen pasando.

**Pendiente de que el usuario pruebe**: configurar `LLM_API_KEY` con su key de Groq o
NVIDIA en `backend/.env` (ver `.env.example`, tiene ambas opciones comentadas) y correr
`POST /jobs/enrich` / `POST /search` / la carta de presentación / el autofill de la
extensión contra el proveedor real — no se pudo probar con una key real en este
sandbox (no hay red de salida a Groq/NVIDIA ni las credenciales), así que esta parte
solo está verificada con mocks.

## Preferencias de búsqueda: idiomas + ciudad para modalidad presencial

El usuario reportó que los avisos de RemoteOK vienen en varios idiomas (no solo
inglés) y quería poder filtrarlos, y además que los avisos presenciales solo se
muestren si están en Ciudad Autónoma de Buenos Aires — ambos configurables desde la
UI, no hardcodeados.

- **Idioma real, no hardcodeado**: `remoteok.py` mandaba `language=JobLanguage.EN`
  fijo para todos los avisos, sin mirar el contenido — por eso el usuario veía avisos
  en portugués clasificados como inglés. Se agregó `services/ingestion/
  language_detection.py` con `detect_job_language()`, que usa la librería `langdetect`
  (heurística estadística local, determinística con `DetectorFactory.seed = 0`, sin
  llamar a ningún proveedor de IA — no viola la regla de CLAUDE.md de no meter
  llamadas a Claude/Voyage en un adapter). Se agregaron `JobLanguage.PT` y
  `JobLanguage.OTHER` al enum (migración `0002_job_language_pt_other.py`, `ALTER TYPE
  ... ADD VALUE IF NOT EXISTS` — Postgres no soporta downgrade de valores de enum sin
  recrear el tipo, documentado como tal).
- **Filtro por idioma + ubicación presencial**: nuevo `services/search/filters.py`
  con `build_job_filters(languages, onsite_location)`, compartido entre `GET /jobs`
  (ahora acepta `languages` repetido y `onsite_location`) y `POST /search` (mismos
  campos en el body). La regla de ubicación es: si `modality == onsite`, solo pasa si
  `location_raw` contiene el texto configurado; avisos remotos/híbridos o sin
  modalidad todavía (enrichment pendiente) nunca se filtran por esto.
- **UI**: `usePreferences.ts` (mismo patrón localStorage que el perfil) guarda
  `languages` (default `["es","en"]`) y `onsiteLocation` (default "Ciudad Autónoma de
  Buenos Aires, Argentina") + un toggle para activar/desactivar esa restricción.
  Panel nuevo `SearchPreferencesPanel.tsx`, accesible desde el botón "Preferencias" en
  `JobInbox`. Cada fetch (keyword y semántica) manda las preferencias vigentes.
- Tests nuevos: detección de idioma real en `test_remoteok.py` (portugués), filtro por
  idioma y por ubicación presencial en `test_jobs.py` (incluye el caso "no afecta
  avisos remotos"). 42/42 tests backend. Frontend: `tsc --noEmit` y `npm run build`
  pasan limpio.

**Importante para el usuario, mismo patrón que el fix de encoding**: el campo
`language` de los ~100 avisos ya ingeridos quedó grabado como `en` a secas (el bug
viejo), así que el filtro por idioma no les va a pegar bien hasta reingestar. Después
de levantar el backend con esta migración aplicada (`alembic upgrade head`), correr
`POST /jobs/ingest/remoteok` de nuevo para que el dedup por `(source_id, external_id)`
actualice el idioma real de cada aviso ya existente.

## HTML crudo en la descripción + mojibake de origen (no de nuestro parseo)

Dos bugs más encontrados al testear la UI en vivo:

1. **`<br>`/`<p>`/`&amp;` literales en la UI**: RemoteOK devuelve título/empresa/
   descripción con HTML embebido, y como React escapa el texto en vez de renderizarlo
   como HTML, se veían los tags y entidades literales. Fix en
   `services/ingestion/text_cleaning.py` (`strip_html`/`strip_html_inline`): saca tags
   convirtiendo los de bloque (`<br>`, `</p>`, `</li>`, etc.) en saltos de línea,
   decodifica entidades con `html.unescape`.
2. **Mojibake que sobrevivía incluso con la decodificación UTF-8 ya arreglada**: no
   era un bug nuestro esta vez — algunos avisos de RemoteOK ya vienen corruptos desde
   el origen (antes de que los toquemos). Se agregó `ftfy` (librería hecha
   específicamente para reparar mojibake) — best-effort, corrupciones de varias
   vueltas no siempre se reconstruyen del todo.

Ambos se aplican en `remoteok.py` antes de guardar nada. Script de backfill
`scripts/clean_raw_text.py` (mismo patrón que `recompute_languages.py`) para
limpiar los avisos ya guardados sin depender de reingerir. Tests nuevos en
`test_remoteok.py` (HTML con tags/entidades, mojibake real de origen). 44/44 tests.

## Bug real en "Búsqueda con IA": no estaba colgada, tardaba ~7s en fallar

El usuario reportó que el botón de búsqueda con IA "no hacía nada". Reproducido con
Playwright contra un backend real: el fetch fallaba (500, sin `VOYAGE_API_KEY` en ese
momento), pero como el `QueryClient` de React Query no tenía configurado `retry`,
usaba el default (3 reintentos con backoff exponencial ≈ 1s + 2s + 4s), así que
tardaba ~7 segundos en mostrar el error — se leía como que estaba colgado, no como un
fallo. Fix: `retry: 1` en `main.tsx`, y el mensaje de error en `JobInbox.tsx` ahora es
específico para el modo semántico en vez del genérico compartido con la búsqueda por
keyword.

De paso se probó a fondo la búsqueda por palabra clave (español, sin resultados, texto
vacío, volver a la lista completa) contra una base sqlite sembrada a mano — sin bugs,
funciona bien. La sospecha es que la contaminación con el botón de IA roto generó la
sensación de que "la búsqueda" en general no andaba.

## Embeddings: de Voyage AI a Ollama local

El usuario no tiene (ni quiere pagar) una API key de Voyage. Mismo criterio que ya se
aplicó para el chat (Groq/NVIDIA en vez de Anthropic): mover los embeddings a un
proveedor gratis/local. Se eligió **Ollama** (ya lo tiene corriendo para el chat, en su
GPU) con el modelo **`mxbai-embed-large`** — elegido puntualmente porque genera
vectores de **1024 dimensiones**, igual que `EMBEDDING_DIM` en `job_posting.py`, así
se evita una migración de la columna `vector` en Postgres.

- `embeddings.py` reescrito para usar `AsyncOpenAI` (mismo cliente y patrón que
  `llm_client.py`) apuntado a `EMBEDDING_BASE_URL` (default
  `http://localhost:11434/v1`, el endpoint OpenAI-compatible de Ollama) en vez del SDK
  propio de `voyageai`.
- `core/config.py`: `embedding_api_key` / `embedding_base_url` / `embedding_model`
  reemplazan a `voyage_api_key` / `voyage_model`. Mismo criterio que `LLM_*`: cambiar
  de proveedor es solo cambiar estas tres variables, sin tocar código.
- Se sacó la dependencia `voyageai` de `pyproject.toml` (ya no hace falta, `openai`
  cubre chat y embeddings).
- Tests: `test_embeddings.py` reescrito con fakes con la forma de respuesta de
  embeddings de OpenAI (`response.data[i].embedding`) en vez de los fakes de
  `voyageai`. 44/44 tests siguen pasando.

**Pendiente de que el usuario corra**: `ollama pull mxbai-embed-large` (una sola vez,
descarga el modelo) y confirmar que `POST /search` funciona de punta a punta con avisos
reales — no se pudo probar contra un Ollama real en este sandbox (no hay Ollama
instalado acá), solo verificado con mocks + que el cliente apunta al endpoint correcto.
