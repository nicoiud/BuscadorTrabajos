# BuscadorTrabajos Autofill (extensión de navegador)

Extensión tipo LastPass: completa los campos de un formulario de postulación (nombre,
email, teléfono, LinkedIn, y preguntas abiertas vía IA) con tu perfil guardado
**localmente en el navegador**. Funciona en cualquier sitio (LinkedIn, Computrabajo,
el que sea) porque un content script tiene permiso del navegador para leer y escribir
el DOM de la página que estás mirando — el mismo mecanismo que usan los gestores de
contraseñas.

## Regla de seguridad, no negociable

**Nunca envía el formulario.** Solo completa campos y los resalta para que los
revises. Vos apretás "enviar" en el sitio original, no la extensión. No pide ni
guarda credenciales de ningún sitio de terceros.

## Cómo probarla localmente

1. Arrancá el backend (`cd backend && uvicorn app.main:app --reload --app-dir src`) —
   la extensión llama a `POST /api/v1/autofill/answer` para las preguntas de texto
   libre. Necesita `ANTHROPIC_API_KEY` configurada para esa parte; el resto (campos
   estructurados: nombre/email/teléfono/etc.) funciona sin backend, es 100% local.
2. En Chrome/Edge: `chrome://extensions` → activar "Modo desarrollador" → "Cargar
   descomprimida" → seleccionar esta carpeta (`extension/`).
3. Click derecho en el ícono de la extensión → "Opciones", completá tu perfil, "Guardar".
4. Andá a cualquier página con un formulario, click en el ícono de la extensión →
   "Rellenar este formulario".
5. Revisá los campos completados (quedan resaltados en violeta) antes de enviar el
   formulario vos mismo.

## Cómo funciona por dentro

- `manifest.json` — Manifest V3. Pide `activeTab` + `scripting` (no `<all_urls>` de
  entrada) para que el content script solo se inyecte cuando vos apretás el botón del
  popup, no automáticamente en cada página que visitás.
- `popup.html`/`popup.js` — botón que inyecta `content.js` en la pestaña activa.
- `content.js` — recorre `input`/`textarea` visibles, matchea por label/placeholder/
  name contra un diccionario de heurísticas (email, teléfono, LinkedIn, etc.) y
  completa directo desde el perfil. Para `textarea` que parecen preguntas abiertas
  (terminan en "?", contienen "por qué"/"cuéntanos"/"why"/etc.) pide una respuesta
  generada con IA — como máximo 5 por formulario, para no disparar de más.
- `background.js` — el content script no puede llamar directo a la API del backend
  sin toparse con CORS/CSP de la página que estás mirando, así que le manda un mensaje
  al service worker (`chrome.runtime.sendMessage`), que sí puede llamar a la API
  gracias a `host_permissions` (declarado para `localhost:8000` por default; si
  cambiás la URL en Opciones a otro dominio, el navegador te pide permiso para ese
  dominio nuevo vía `chrome.permissions.request`).
- `options.html`/`options.js` — perfil estructurado guardado en `chrome.storage.local`
  (nunca en el backend, salvo el texto que mandás puntualmente para generar una
  respuesta de IA).

## Limitaciones conocidas

- Solo completa `<input>`/`<textarea>` — no toca `<select>` (elegir mal una opción
  sería peor que no completarla).
- Formularios armados con widgets custom (no `<input>`/`<textarea>` reales) pueden no
  detectarse.
- Si el formulario está en un `<iframe>` de otro dominio, la extensión necesita
  permiso para ese dominio también.
