const $ = (id) => document.getElementById(id);


async function refreshStatus() {
  const { paused, hostsGranted, apiToken } = await browser.storage.local.get([
    "paused", "hostsGranted", "apiToken",
  ]);
  $("pause-toggle").checked = !!paused;
  $("hosts-status").textContent = hostsGranted ? "concedidos" : "faltan";
  if (apiToken) $("token-input").value = apiToken;

  try {
    const r = await fetch("http://127.0.0.1:8000/health");
    $("backend-status").textContent = r.ok ? "ok" : `error ${r.status}`;
  } catch {
    $("backend-status").textContent = "sin conexión";
  }
}


function addEvent(text) {
  const li = document.createElement("li");
  li.textContent = `${new Date().toLocaleTimeString()} — ${text}`;
  $("events").prepend(li);
  while ($("events").children.length > 20) {
    $("events").lastChild.remove();
  }
}


$("pause-toggle").addEventListener("change", async (e) => {
  await browser.storage.local.set({ paused: e.target.checked });
  addEvent(e.target.checked ? "pausado" : "reanudado");
});


$("token-save").addEventListener("click", async () => {
  await browser.storage.local.set({ apiToken: $("token-input").value.trim() });
  addEvent("token guardado");
});


browser.runtime.onMessage.addListener((message) => {
  if (message.type === "event_ingested") {
    const { result } = message;
    addEvent(`msg=${result.message_id} → ${result.decision} (${result.rule_applied})`);
  } else if (message.type === "event_error") {
    addEvent(`error: ${message.error}`);
  }
});


refreshStatus();
setInterval(refreshStatus, 10000);