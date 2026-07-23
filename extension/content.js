// Injected on demand (via chrome.scripting.executeScript, triggered by the popup
// button) into the active tab. Fills form fields on the CURRENT page with the
// locally-stored profile. Never touches a submit/send button — the user reviews and
// submits the form themselves.
(async function autofillBuscadorTrabajos() {
  const DEFAULT_API_BASE = "http://localhost:8000/api/v1";
  const MAX_AI_FIELDS = 5;

  const HEURISTICS = [
    { field: "email", patterns: [/e.?mail/i, /correo/i] },
    { field: "phone", patterns: [/phone/i, /tel[eé]fono/i, /celular/i, /m[oó]vil/i] },
    { field: "linkedinUrl", patterns: [/linkedin/i] },
    { field: "portfolioUrl", patterns: [/portfolio/i, /website/i, /sitio\s*web/i, /github/i] },
    {
      field: "location",
      patterns: [/location/i, /ciudad/i, /ubicaci[oó]n/i, /^city$/i, /direcci[oó]n/i],
    },
    {
      field: "yearsExperience",
      patterns: [/years?.{0,3}experience/i, /a[nñ]os.{0,3}experiencia/i],
    },
    { field: "fullName", patterns: [/full.?name/i, /nombre\s*completo/i] },
    { field: "lastName", patterns: [/last.?name/i, /surname/i, /apellido/i] },
    { field: "firstName", patterns: [/first.?name/i, /given.?name/i, /^nombres?$/i] },
  ];

  const OPEN_QUESTION_HINTS = [
    /\?\s*$/,
    /why/i,
    /por\s*qu[eé]/i,
    /cu[eé]ntanos/i,
    /describe/i,
    /cover\s*letter/i,
    /carta\s*de\s*presentaci[oó]n/i,
    /motivaci[oó]n/i,
  ];

  function getLabelText(el) {
    const parts = [];
    if (el.labels && el.labels.length > 0) parts.push(el.labels[0].innerText);
    if (el.getAttribute("aria-label")) parts.push(el.getAttribute("aria-label"));
    if (el.placeholder) parts.push(el.placeholder);
    if (el.name) parts.push(el.name.replace(/[-_]/g, " "));
    if (el.id) parts.push(el.id.replace(/[-_]/g, " "));
    return parts.join(" ").trim();
  }

  function isVisible(el) {
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== "hidden";
  }

  function isFillableField(el) {
    if (el.disabled || el.readOnly) return false;
    const skipTypes = [
      "hidden",
      "submit",
      "button",
      "checkbox",
      "radio",
      "file",
      "password",
      "image",
      "reset",
    ];
    if (el.type && skipTypes.includes(el.type)) return false;
    return isVisible(el);
  }

  function setFieldValue(el, value) {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.style.outline = "2px solid #6366f1";
    el.style.backgroundColor = "#eef2ff";
  }

  function looksLikeOpenQuestion(labelText) {
    return OPEN_QUESTION_HINTS.some((p) => p.test(labelText));
  }

  const stored = await chrome.storage.local.get(["profile", "apiBaseUrl"]);
  const profile = stored.profile;
  const apiBaseUrl = stored.apiBaseUrl || DEFAULT_API_BASE;

  if (!profile) {
    alert(
      'BuscadorTrabajos: todavía no cargaste tu perfil. Click derecho en el ícono de la extensión → "Opciones" para cargarlo.',
    );
    return;
  }

  const candidates = Array.from(document.querySelectorAll("input, textarea")).filter(
    isFillableField,
  );

  let filledCount = 0;
  const freeformTargets = [];

  for (const el of candidates) {
    const labelText = getLabelText(el);
    const lower = labelText.toLowerCase();
    let matchedField = null;

    for (const { field, patterns } of HEURISTICS) {
      if (patterns.some((p) => p.test(lower))) {
        matchedField = field;
        break;
      }
    }

    if (matchedField && profile[matchedField]) {
      setFieldValue(el, String(profile[matchedField]));
      filledCount++;
      continue;
    }

    if (el.tagName === "TEXTAREA" && (looksLikeOpenQuestion(lower) || lower.length === 0)) {
      freeformTargets.push({ el, labelText: labelText || "Pregunta abierta del formulario" });
    }
  }

  const aiTargets = freeformTargets.slice(0, MAX_AI_FIELDS);
  for (const { el, labelText } of aiTargets) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: "GENERATE_ANSWER",
        fieldLabel: labelText,
        profileText: profile.summary || "",
        apiBaseUrl,
      });
      if (response?.answer) {
        setFieldValue(el, response.answer);
        filledCount++;
      }
    } catch (err) {
      console.warn("BuscadorTrabajos autofill: no se pudo generar respuesta para", labelText, err);
    }
  }

  alert(
    `BuscadorTrabajos completó ${filledCount} campo(s). Revisá todo antes de enviar — la extensión nunca envía el formulario por vos.`,
  );
})();
