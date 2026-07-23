const DEFAULT_API_BASE = "http://localhost:8000/api/v1";
const FIELDS = [
  "firstName",
  "lastName",
  "fullName",
  "email",
  "phone",
  "linkedinUrl",
  "portfolioUrl",
  "location",
  "yearsExperience",
  "summary",
];

async function load() {
  const { profile, apiBaseUrl } = await chrome.storage.local.get(["profile", "apiBaseUrl"]);
  for (const field of FIELDS) {
    const el = document.getElementById(field);
    if (el && profile?.[field]) el.value = profile[field];
  }
  document.getElementById("apiBaseUrl").value = apiBaseUrl || DEFAULT_API_BASE;
}

async function save() {
  const profile = {};
  for (const field of FIELDS) {
    profile[field] = document.getElementById(field).value.trim();
  }
  const apiBaseUrl = document.getElementById("apiBaseUrl").value.trim() || DEFAULT_API_BASE;

  if (!apiBaseUrl.startsWith("http://localhost") && !apiBaseUrl.startsWith("http://127.0.0.1")) {
    try {
      const origin = new URL(apiBaseUrl).origin + "/*";
      const granted = await chrome.permissions.request({ origins: [origin] });
      if (!granted) {
        document.getElementById("saved").textContent =
          "Sin permiso para ese dominio, la extensión no va a poder llamarlo.";
        document.getElementById("saved").style.color = "#dc2626";
        return;
      }
    } catch {
      document.getElementById("saved").textContent = "URL de API inválida.";
      document.getElementById("saved").style.color = "#dc2626";
      return;
    }
  }

  await chrome.storage.local.set({ profile, apiBaseUrl });
  const savedEl = document.getElementById("saved");
  savedEl.style.color = "#16a34a";
  savedEl.textContent = "Guardado ✓";
  setTimeout(() => (savedEl.textContent = ""), 2000);
}

document.getElementById("saveBtn").addEventListener("click", save);
load();
