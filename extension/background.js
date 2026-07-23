// Runs in the extension's service worker context. Content scripts (which run inside
// the page you're filling) message this file to reach the BuscadorTrabajos API,
// because a background fetch with host_permissions bypasses the page's CORS/CSP
// restrictions in a way a content-script fetch cannot.
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "GENERATE_ANSWER") return false;

  (async () => {
    try {
      const res = await fetch(`${message.apiBaseUrl}/autofill/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          field_label: message.fieldLabel,
          profile_text: message.profileText,
        }),
      });
      if (!res.ok) {
        sendResponse({ error: `HTTP ${res.status}` });
        return;
      }
      const data = await res.json();
      sendResponse({ answer: data.answer });
    } catch (err) {
      sendResponse({ error: String(err) });
    }
  })();

  return true; // keep the message channel open for the async sendResponse above
});
