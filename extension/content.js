// Manifest V3 content script — runs in the context of every tab.
// Extracts visible page text and POSTs it (along with the URL) to /classify
// so the server can map the content to a learning node without needing Rtrvr.ai.

const BACKEND_URL = "http://localhost:8000";
const SESSION_ID = "default";
const DEBOUNCE_MS = 2000;

let debounceTimer = null;

function extractVisibleText() {
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        const el = node.parentElement;
        if (!el) return NodeFilter.FILTER_REJECT;
        const tag = el.tagName.toLowerCase();
        if (["script", "style", "noscript", "nav", "footer", "header"].includes(tag))
          return NodeFilter.FILTER_REJECT;
        const style = window.getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden") return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    }
  );

  const parts = [];
  let node;
  while ((node = walker.nextNode())) {
    const text = node.textContent?.trim();
    if (text && text.length > 2) parts.push(text);
  }
  return parts.join(" ").slice(0, 10000);
}

async function classify() {
  const pageUrl = window.location.href;

  // Only classify HTTP pages — skip extensions, devtools, etc.
  if (!pageUrl.startsWith("http")) return;

  // Extract visible text here and send it directly to avoid Rtrvr.ai round-trip
  const pageText = extractVisibleText();

  try {
    await fetch(`${BACKEND_URL}/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_url: pageUrl, session_id: SESSION_ID, page_text: pageText }),
    });
  } catch {
    // Silently ignore — backend may not be running during development
  }
}

function scheduleClassify() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(classify, DEBOUNCE_MS);
}

// Trigger on initial load and on SPA navigation
scheduleClassify();

const _pushState = history.pushState.bind(history);
history.pushState = (...args) => {
  _pushState(...args);
  scheduleClassify();
};
window.addEventListener("popstate", scheduleClassify);
