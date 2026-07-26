// Manifest V3 content script — runs in the context of every tab.

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
  if (!pageUrl.startsWith("http")) return;

  const pageText = extractVisibleText();

  try {
    await chrome.runtime.sendMessage({
      type: "classify",
      payload: { page_url: pageUrl, session_id: "default", page_text: pageText },
    });
  } catch {
    // Extension context may be invalidated — ignore
  }
}

function normaliseUrl(raw) {
  try {
    const u = new URL(raw);
    u.hash = "";
    u.searchParams.sort();
    let s = u.toString();
    if (s.endsWith("/")) s = s.slice(0, -1);
    return s;
  } catch {
    return raw;
  }
}

async function reportResourceVisit() {
  const pageUrl = window.location.href;
  if (!pageUrl.startsWith("http")) return;

  try {
    const res = await chrome.runtime.sendMessage({ type: "get-resource-map" });
    if (!res?.ok || !res.data) return;

    const resourceMap = res.data;
    const normPage = normaliseUrl(pageUrl);

    for (const [nodeId, urls] of Object.entries(resourceMap)) {
      for (const url of urls) {
        const normResource = normaliseUrl(url);
        if (normPage === normResource || normPage.startsWith(normResource)) {
          console.log(`[Learnograph Extension] 🎯 Resource match found for node "${nodeId}":`, pageUrl);
          await chrome.runtime.sendMessage({
            type: "report-resource-visit",
            payload: {
              session_id: "default",
              node_id: nodeId,
              resource_url: url,
            },
          });
          return;
        }
      }
    }
  } catch (err) {
    console.warn("[Learnograph Extension] Notice:", err);
  }
}

function scheduleActions() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    await classify();
    await reportResourceVisit();
  }, DEBOUNCE_MS);
}

scheduleActions();

const _pushState = history.pushState.bind(history);
history.pushState = (...args) => {
  _pushState(...args);
  scheduleActions();
};
window.addEventListener("popstate", scheduleActions);
