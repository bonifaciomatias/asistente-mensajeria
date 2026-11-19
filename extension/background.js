const BACKEND = "http://127.0.0.1:8000";
const REQUIRED_HOSTS = { origins: ["https://web.telegram.org/*", "http://127.0.0.1:8000/*"] };


async function getToken() {
  const { apiToken } = await browser.storage.local.get("apiToken");
  return apiToken || "cambiame-en-produccion";
}


async function ensureHosts() {
  const granted = await browser.permissions.contains(REQUIRED_HOSTS);
  await browser.storage.local.set({ hostsGranted: granted });
  return granted;
}


async function apiFetch(path, options = {}) {
  const token = await getToken();
  const resp = await fetch(`${BACKEND}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`backend_${resp.status}: ${text.slice(0, 200)}`);
  }
  return resp.json();
}


browser.runtime.onMessage.addListener(async (message, sender) => {
  if (message.type === "ingest") {
    const { paused } = await browser.storage.local.get("paused");
    if (paused) return { ok: false, reason: "paused" };
    const hostsOk = await ensureHosts();
    if (!hostsOk) return { ok: false, reason: "hosts_not_granted" };

    try {
      const result = await apiFetch("/ingest", {
        method: "POST",
        body: JSON.stringify(message.payload),
      });
      browser.runtime.sendMessage({ type: "event_ingested", result }).catch(() => {});
      return { ok: true, result };
    } catch (err) {
      browser.runtime.sendMessage({ type: "event_error", error: String(err) }).catch(() => {});
      return { ok: false, reason: String(err) };
    }
  }

  if (message.type === "write") {
    try {
      const result = await apiFetch("/write", {
        method: "POST",
        body: JSON.stringify(message.payload),
      });
      return { ok: true, result };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }

  if (message.type === "confirm_sent") {
    try {
      await apiFetch(`/drafts/${message.draftId}/sent`, { method: "POST" });
      browser.runtime.sendMessage({
        type: "draft_sent",
        draftId: message.draftId,
        text: (message.text || "").slice(0, 80),
      }).catch(() => {});
      return { ok: true };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }

  if (message.type === "confirm_failed") {
    try {
      await apiFetch(`/drafts/${message.draftId}/failed`, {
        method: "POST",
        body: JSON.stringify({ reason: message.reason }),
      });
      browser.runtime.sendMessage({
        type: "draft_failed",
        draftId: message.draftId,
        reason: message.reason,
      }).catch(() => {});
      return { ok: true };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }
  if (message.type === "get_status") {
    try {
      const result = await apiFetch("/status", { method: "GET" });
      return { ok: true, result };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }   
});


browser.action.onClicked.addListener(() => browser.sidebarAction.toggle());
browser.runtime.onInstalled.addListener(() => ensureHosts());
browser.runtime.onStartup.addListener(() => ensureHosts());