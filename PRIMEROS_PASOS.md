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

## Más fuentes: Greenhouse + Lever genéricos (LinkedIn y ZonaJobs, no todavía)

El usuario pidió sumar muchas fuentes más — LinkedIn, ZonaJobs, y "sitios web de
empresas" en general — porque notó que RemoteOK es un feed fijo de ~100 avisos
recientes (sin búsqueda), así que el archivo no crecía en base a lo que buscaba.

- **LinkedIn: reconfirmado fuera de alcance** (regla explícita de `CLAUDE.md` — ToS +
  antecedente legal hiQ Labs v. LinkedIn). Se le explicó el motivo al usuario antes de
  tocar código, no se implementó.
- **"Sitios web de empresas" → Greenhouse + Lever genéricos**: en vez de un adapter
  por empresa (inviable, cada sitio tiene su propia estructura), se armaron DOS
  adapters genéricos parametrizados por empresa — `GreenhouseAdapter(board=...)` y
  `LeverAdapter(company=...)` — que cubren cualquier empresa que use esas plataformas
  como ATS (son muchísimas, de startups a empresas grandes). Configurables por
  `GREENHOUSE_BOARDS`/`LEVER_COMPANIES` en `.env` (slugs separados por coma), sin
  tocar código para agregar una empresa nueva. Son APIs públicas de job board, no
  scraping — sin problema de ToS.
- **ZonaJobs/Bumeran/Computrabajo: todavía no implementado**. Requieren scraping de
  HTML (no exponen API pública) y no hay red de salida en este sandbox para
  verificar `robots.txt` ni la estructura real de la página — no tiene sentido
  escribir un parser a ciegas. Falta que el usuario (o una sesión con acceso a
  internet) confirme `robots.txt` y pase una muestra de HTML real de una página de
  resultados y una de detalle de aviso.
- **Refactor en `runner.py`**: los defaults para crear la fila en `sources` (antes un
  diccionario estático `_SOURCE_DEFAULTS` indexado por slug fijo) ahora los expone
  cada adapter (`SourceAdapter.source_defaults()`) — necesario porque
  `GreenhouseAdapter`/`LeverAdapter` tienen un slug distinto por instancia
  (`greenhouse-stripe`, `lever-netflix`, etc.), no uno fijo por clase. Se agregó
  también el kill-switch por fuente (`sources.enabled`, ya documentado en
  `CLAUDE.md` pero nunca antes chequeado en código) y `ingest_all_sources()`, que
  corre RemoteOK + todas las empresas configuradas y aísla el fallo de una fuente
  puntual (red, HTTP, parseo) sin abortar las demás — mismo patrón que ya se usó en
  `pipeline.py` para el enrichment.
- **API**: nuevo `POST /jobs/ingest` (corre todas las fuentes configuradas, devuelve
  un resumen con el detalle y error por fuente) — `POST /jobs/ingest/remoteok` se
  mantiene para poder correr solo esa fuente puntual. El botón "Actualizar ofertas"
  del frontend ahora pega al endpoint agregado y muestra el error de cualquier fuente
  que haya fallado, sin ocultarlo.
- Tests nuevos: `test_greenhouse.py`, `test_lever.py` (parseo, HTML/entidades,
  defaults de nombre de empresa) y en `test_runner.py` (kill-switch, agregado
  multi-fuente, aislamiento de una fuente rota). 53/53 tests backend.

**Importante para el usuario — esto no está verificado contra las APIs reales**: el
parseo de Greenhouse/Lever está escrito contra el contrato documentado de sus APIs
públicas (estables y bien conocidas), pero este sandbox no tiene salida de red para
probarlos contra una empresa real antes de este commit. Es muy probable que ande tal
cual, pero hay que confirmarlo: configurar `GREENHOUSE_BOARDS`/`LEVER_COMPANIES` con
1-2 empresas reales, correr `POST /jobs/ingest`, y si algún campo viene distinto al
esperado (nombres de campos, formato de fecha, etc.) avisar para ajustar el parser —
mismo proceso iterativo que se usó para ir puliendo el adapter de RemoteOK.

## We Work Remotely + pedido consolidado de fuentes por scraping

El usuario pidió sumar "muchas" fuentes para que el buscador nuclee de varios sitios:
ZonaJobs, Computrabajo, Bumeran ("boomerang"), WeRemoto y Workana.

- **We Work Remotely agregado**: feeds RSS por categoría (pensados para consumo
  automatizado, no scraping) — `WeWorkRemotelyAdapter`, configurable por
  `WEWORKREMOTELY_FEED_URLS` (una o más URLs separadas por coma). Parsea con
  `feedparser`; el título del feed viene como `"Empresa: Puesto"`, se separa por el
  primer `": "`. Cada URL de categoría se fetchea por separado y una que falle
  (rota, 500, etc.) no aborta las demás — mismo patrón de aislamiento que
  `ingest_all_sources`. Default: solo la categoría de programación, porque no se
  pudo verificar el resto de las URLs de categoría contra el sitio real (mismo
  problema de red del sandbox). 56/56 tests backend.
- **ZonaJobs, Computrabajo, Bumeran, WeRemoto, Workana: ninguno implementado
  todavía**. Los cinco necesitan scraping de HTML (no se conoce una API pública para
  ninguno) y este sandbox no tiene salida de red — no se puede chequear `robots.txt`,
  ver si hay una API JSON interna, ni la estructura real de una página. Escribir un
  parser HTML a ciegas es el tipo de cosa que se rompe apenas se prueba contra datos
  reales (o peor, "funciona" pero devuelve basura silenciosamente).

**Pendiente del usuario, para poder construir estos cinco bien a la primera** (por
cada sitio: zonajobs.com.ar, computrabajo.com.ar, bumeran.com.ar, weremoto.com,
workana.com):
1. `robots.txt` del sitio (`curl https://www.SITIO/robots.txt` desde su cmd, que sí
   tiene salida de red).
2. Chequear si hay una API JSON interna antes de asumir que hay que scrapear HTML:
   abrir la página de resultados en Chrome, F12 → pestaña Network → filtro
   Fetch/XHR → recargar → ver si algún request devuelve JSON con los avisos. Si lo
   hay, es mucho más robusto consumir eso que parsear HTML — pasar la URL de ese
   request (botón derecho → Copy → Copy as cURL).
3. Si no hay API interna: una muestra de HTML real de una página de resultados y una
   de detalle de aviso (Ctrl+U para ver el código fuente, o guardar la página).

Con eso se arma cada adapter respetando `robots.txt`/rate-limit como ya exige
`CLAUDE.md` para scrapers nuevos, en vez de adivinar.

**Pendiente de decisión del usuario**: la idea de "que los avisos sean para tu perfil"
(matching automático contra un CV/perfil guardado, con score) es la Fase 3 del plan
original — todavía no existe (`profiles`/`match_scores` no están implementados; el
"perfil" de hoy es solo un texto en `localStorage` que alimenta la carta de
presentación). Atajo disponible ya mismo sin construir nada nuevo: pegar el resumen
del perfil/CV directamente en el campo de "Búsqueda con IA" — el embedding de esa
búsqueda va a rankear los avisos por similitud semántica al perfil, que es
90% del valor sin el trabajo de guardar `profiles`/`match_scores` y una pantalla de
scoring dedicada. Falta confirmar con el usuario si igual quiere la Fase 3 completa
(perfil guardado + score visible por aviso, sin tener que re-pegar el texto cada vez)
más adelante.

## ZonaJobs: API interna encontrada vía DevTools, no HTML scraping

El usuario hizo el trabajo de campo que se le había pedido: `robots.txt` (no bloquea
nada relevante, y lista `sitemap_avisos_zj.xml`) y una captura del Network tab del
navegador en una página de aviso y en una de resultados. Resultado: **ZonaJobs es una
SPA** — el HTML servido está vacío (`<div id="root">` con un spinner, contenido real
pintado por JS), así que "ver código fuente" nunca iba a servir para esto. Pero el
propio frontend de ZonaJobs pega a una API JSON interna, y esa sí sirve datos
completos:

- **Listado**: `GET /api/avisos/searchV2?pageSize=20&page=0&sort=RELEVANTES` — trae
  varios avisos por pedido, con `detalle` (descripción) ya en texto plano, sin HTML.
- **Detalle**: `GET /api/candidates/fichaAvisoNormalizada/{id}` — un aviso completo;
  se usa solo para conseguir `seoFriendlyUrl` (la URL linda), que el listado no trae.

`ZonaJobsAdapter` (`services/ingestion/zonajobs.py`) combina los dos: un pedido al
listado, y un pedido de detalle por cada aviso (con `await asyncio.sleep
(scraper_default_delay_seconds)` entre cada uno para no hostigar el servidor). Si el
detalle de un aviso puntual falla, no se pierde el aviso — se arma con los campos que
ya trajo el listado y una URL de fallback (`/empleos.html?aviso={id}`) en vez de la
linda. `language`/`region` van hardcodeados (`es`/`latam`) porque, a diferencia de
RemoteOK, ZonaJobs es un sitio de un solo país e idioma — no hace falta
`detect_job_language` acá. `source_type = SCRAPE` (no `API`) porque es una API interna
no documentada/no pública, a diferencia de Greenhouse/Lever.

Dato para lo que sigue: el JS del sitio tiene una variable `window.SITE_ID` que
distingue `"ZJAR"` (ZonaJobs) de `"BMVE"` (Bumeran) — mismo bundle para los dos, así
que **Bumeran probablemente use la misma API**, solo cambiando el dominio. Falta
confirmarlo antes de asumirlo (pedirle al usuario un curl rápido a la URL equivalente
en bumeran.com.ar).

Tests nuevos: `test_zonajobs.py` (combinación listado+detalle, fallback cuando el
detalle falla, default de empresa confidencial). 59/59 tests backend.

## Corrección: ZonaJobs también está bloqueado — se saca de la corrida automática

El usuario probó `POST /jobs/ingest` contra el sitio real y la API de ZonaJobs
devolvió **403 Forbidden** — a diferencia de lo que asumí, el hecho de que
`robots.txt` no la bloqueara no significaba que el pedido fuera a pasar: el servidor
mismo rechaza pedidos que no vienen de una sesión de browser real. Mismo tipo de
señal que ya habíamos visto con Bumeran (ahí era Cloudflare con captcha; acá es un
403 liso), solo que esta vez apareció después de commitear el adapter en vez de
antes — debí haber probado esto (o al menos advertido el riesgo) antes de darlo por
andando.

Corrección aplicada: `ZonaJobsAdapter` se sacó de `_configured_adapters()` en
`runner.py` (con un comentario explicando por qué) — el código y los tests quedan
porque siguen siendo correctos como implementación, simplemente no se ejecutan
solos. Agregar headers (`Referer`/`Origin`) para que el pedido parezca venir del
propio frontend del sitio cruzaría la regla de `CLAUDE.md` de nunca simular un
browser para evadir bloqueos, así que no se intentó. Se removieron los mocks de
ZonaJobs de `test_runner.py` (ya no corre por defecto ahí). 59/59 tests backend.

**Estado real de fuentes por scraping/API-no-pública**: ZonaJobs y Bumeran quedan en
la misma categoría que LinkedIn — bloqueados, no implementados, por la misma razón de
fondo (el sitio activamente no quiere tráfico automatizado ahí). Quedan pendientes
con el mismo proceso de investigación: Computrabajo, WeRemoto y Workana — con la
advertencia de que si el resultado es el mismo (403/Cloudflare), tampoco se van a
implementar.

## Bug real en extractor.py: el modelo local devolvía basura estructural

El usuario probó "Búsqueda con IA" con "analista funcional" y con "business analyst"
y ambas devolvieron resultados básicamente iguales e irrelevantes (avisos de prueba
tipo "This is a test job", formularios, etc.) — no era un problema del modelo de
embeddings ni del idioma. Investigando los datos reales devueltos por `curl`, aparecieron
dos bugs de verdad en `extractor.py`:

1. **Eco del schema como valor**: para el aviso "ACT Application Form", el modelo
   local (Ollama, más débil que Groq) devolvió como `title_normalized` el propio
   JSON del schema de la tool (`{"type":"string","description":"...","value":"ACT
   Application Form"}`) en vez del texto esperado — y el código lo guardaba tal
   cual, literal, en la columna.
2. **`requirements` como string en vez de array**: para otro aviso, el modelo mandó
   la lista de requisitos como un string con forma de array (`'["loving the
   company\'s products"...]'`) en vez de un array real. `list(esa_string)` (código
   viejo) la explotó en un array de un carácter por elemento (`["[", "\"", "l",
   "o", "v", ...]`).

Ambos contaminan `_embedding_text()` en `pipeline.py` (arma el texto para el
embedding a partir de `title_normalized`/`summary`/`requirements`), así que el
embedding resultante para esos avisos es básicamente ruido — de ahí que la búsqueda
semántica rankeara cosas sin relación ninguna arriba de todo.

Fix en `extractor.py`: `_clean_text()` (nuevo) detecta el patrón de eco-de-schema e
intenta rescatar el `"value"` de adentro antes de tirar el campo; si no se puede
rescatar, cae al título/empresa crudos (`title_raw`/`company_raw`, que ya tenemos)
en vez de perder el aviso entero. `_clean_requirements()` (nuevo) solo trata un
string como lista si de verdad parsea como JSON-array; si no, devuelve `[]` en vez
de explotarlo en caracteres. De paso, `title_normalized`/`company_normalized`/
`summary` con campo faltante o no reconstruible ya no tiran `ExtractionError` (que
perdía el aviso entero) — usan el fallback crudo, mismo criterio que ya se aplicaba
a seniority/modalidad.

Script `scripts/reset_enrichment.py` para los avisos ya procesados con el bug activo
(no se corrigen solos porque `POST /jobs/enrich` solo toca `pending`) — por default
resetea todos los `done`/`failed` a `pending`; `--only-suspicious` para resetear
solo los que tienen la firma del bug.

Tests nuevos en `test_extractor.py` (eco de schema, requirements como string válido
e inválido, fallback en campos faltantes — se actualizó el test viejo que esperaba
`ExtractionError` ahí, ahora es el comportamiento esperado). 62/62 tests backend.

**Otro hallazgo del mismo debugging, no bloqueante**: solo 31 de 151 avisos tenían
`enrichment_status=done` — la búsqueda semántica solo busca entre esos (requiere
embedding no nulo). "Analizar con IA" procesa de a `ENRICHMENT_BATCH_SIZE` (20) por
click; para poblar bien la búsqueda semántica hace falta correrlo varias veces o
pasar `?limit=` más alto por `curl`. También se vio un caso de texto con caracteres
repetidos/glitcheados en un `summary` generado ("soluúuúss" en vez de "soluções") —
parece ruido propio de un modelo local chico/cuantizado en generación libre (no
tool-calling), no algo sanitizable de forma confiable en código; queda como
limitación conocida, no como bug a arreglar.

## Bug real en el frontend: la lista nunca mostraba más de ~20 puestos

El usuario marcó todos los filtros de idioma (sin restricción de ubicación) después
de un ingest que reportó "124 ofertas procesadas" y reportó que la lista de la
bandeja nunca llegaba a mostrar los 124 — se quedaba corta siempre, sin ninguna
forma de pedir más. Causa real: `GET /jobs` en el backend ya soportaba `offset`/
`limit` desde el principio (con `limit` tope 100 por validación de FastAPI), pero
el frontend nunca los usaba — `fetchJobs()` pedía siempre la página por default
(las primeras 20) y no había ningún mecanismo de paginación en la UI. El número
"124 procesadas" que se ve después del ingest es correcto (viene del resumen de
ingestion, no de la lista), lo que estaba mal era la lista en sí.

Fix, sin tocar el backend (ya soportaba paginación):
- `api/jobs.ts`: `fetchJobs()` ahora acepta `offset`/`limit` y los manda como query
  params a `GET /jobs`.
- `hooks/useJobs.ts`: modo palabra clave reescrito con `useInfiniteQuery` (React
  Query) — acumula páginas de a `PAGE_SIZE=20`, calcula `hasNextPage` comparando
  cuánto se cargó contra el `total` que devuelve el backend. El modo "Búsqueda con
  IA" (semántico) queda como estaba — trae un top-K rankeado de una sola vez, no
  tiene sentido paginarlo. El hook ahora devuelve `{items, total, isLoading,
  isError, hasNextPage, isFetchingNextPage, fetchNextPage}` en vez del objeto crudo
  de React Query.
- `pages/JobInbox.tsx`: consume el nuevo shape del hook, agrega un botón "Cargar
  más (N de total)" al final de la lista, visible solo cuando `hasNextPage` es
  true; debajo de la última página muestra "N de total ofertas" como confirmación
  de que se ve todo.

`npx tsc --noEmit` y `npm run build` sin errores. No hizo falta tocar el backend
(la paginación ya existía en `GET /jobs`, simplemente no se usaba desde el
frontend).
