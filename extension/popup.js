const statusEl = document.getElementById("status");

document.getElementById("fillBtn").addEventListener("click", async () => {
  const { profile } = await chrome.storage.local.get("profile");
  if (!profile || (!profile.email && !profile.summary)) {
    statusEl.textContent = "Completá tu perfil primero (Editar mi perfil).";
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    statusEl.textContent = "No se pudo acceder a la pestaña activa.";
    return;
  }

  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content.js"],
  });
  window.close();
});

document.getElementById("optionsBtn").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});
