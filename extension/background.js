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


async function postIngest(payload) {
  const token = await getToken();
  const resp = await fetch(`${BACKEND}/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`backend_${resp.status}: ${text.slice(0, 200)}`);
  }
  return resp.json();
}


browser.runtime.onMessage.addListener(async (message, sender) => {
  if (message.type !== "ingest") return;

  const { paused } = await browser.storage.local.get("paused");
  if (paused) {
    console.log("[asistente] pausado, evento descartado");
    return { ok: false, reason: "paused" };
  }

  const hostsOk = await ensureHosts();
  if (!hostsOk) {
    console.warn("[asistente] permisos de host no concedidos");
    return { ok: false, reason: "hosts_not_granted" };
  }

  try {
    const result = await postIngest(message.payload);
    // Notificar al sidebar si está abierto.
    browser.runtime.sendMessage({ type: "event_ingested", result }).catch(() => {});
    return { ok: true, result };
  } catch (err) {
    console.error("[asistente] ingest falló:", err);
    browser.runtime.sendMessage({ type: "event_error", error: String(err) }).catch(() => {});
    return { ok: false, reason: String(err) };
  }
});


// Abrir/cerrar el sidebar desde el icono de la barra de herramientas.
browser.action.onClicked.addListener(() => {
  browser.sidebarAction.toggle();
});


browser.runtime.onInstalled.addListener(() => ensureHosts());
browser.runtime.onStartup.addListener(() => ensureHosts());