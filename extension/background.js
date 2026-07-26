// Manifest V3 service worker.
// Handles cross-origin requests to the Learnograph backend on behalf of
// content scripts, avoiding mixed-content (HTTPS→HTTP) blocks.

const BACKEND_URL = "http://localhost:8000";
const SESSION_ID = "default";

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "classify") {
    fetch(`${BACKEND_URL}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg.payload),
    })
      .then(() => sendResponse({ ok: true }))
      .catch((err) => {
        console.error("[Learnograph Background] Classify request failed:", err);
        sendResponse({ ok: false });
      });
    return true;
  }

  if (msg.type === "get-resource-map") {
    fetch(`${BACKEND_URL}/dag/resources/${SESSION_ID}`)
      .then((r) => (r.ok ? r.json() : {}))
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => {
        console.error("[Learnograph Background] Failed to fetch resource map:", err);
        sendResponse({ ok: false, data: {} });
      });
    return true;
  }

  if (msg.type === "report-resource-visit") {
    console.log("[Learnograph Background] 🎯 Reporting resource visit to backend:", msg.payload);
    fetch(`${BACKEND_URL}/resource-visit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg.payload),
    })
      .then((r) => r.json())
      .then((res) => {
        console.log("[Learnograph Background] ✅ Visit recorded response:", res);
        sendResponse({ ok: true, res });
      })
      .catch((err) => {
        console.error("[Learnograph Background] ❌ Failed to record resource visit:", err);
        sendResponse({ ok: false });
      });
    return true;
  }
});

chrome.runtime.onInstalled.addListener(() => {
  console.log("Learnograph extension installed.");
});
