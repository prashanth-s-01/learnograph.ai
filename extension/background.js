// Minimal Manifest V3 service worker.
// The heavy lifting happens in content.js — this file exists to satisfy
// the manifest's "service_worker" field and can be extended for future needs.

chrome.runtime.onInstalled.addListener(() => {
  console.log("Learnograph extension installed.");
});
