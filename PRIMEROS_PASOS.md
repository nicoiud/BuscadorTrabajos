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
2. Endpoint + UI para generar el borrador de carta de presentación/respuestas por
   puesto seleccionado (Claude, reutilizando el patrón de `services/enrichment/`).
3. Extensión de navegador (nuevo componente del repo, ej. `extension/`):
   - Manifest V3, pantalla de opciones para cargar el perfil local (nombre, email,
     teléfono, links, CV/resumen).
   - Content script que detecta campos por label/placeholder/name (heurísticas +
     fallback a Claude para campos ambiguos o de texto libre) y los completa.
   - Sin submit automático, nunca.
4. (Más adelante, no bloqueante) migrar el perfil de la extensión a estar sincronizado
   con el backend cuando exista Fase 4.

Siguiente paso a construir: el punto 2 (asistente de carta de presentación).
