// Adaptador específico de Telegram Web.
// Aísla los selectores frágiles del resto de la lógica.
const TelegramAdapter = (() => {
  // Telegram WebK y WebA tienen estructuras distintas. Estos selectores son
  // deliberadamente amplios y se validan con heurísticas, no con una sola clase.
  const CHAT_PANE_SELECTORS = [
    ".chat-container",
    ".Chat .messages-layout",
    "#column-center .chat",
  ];

  const MESSAGE_NODE_SELECTORS = [
    ".message",                 // WebK
    ".Message",                 // WebA
    "[data-mid]",               // atributo estable en WebK
    "[data-message-id]",        // atributo estable en WebA
  ];

  function findChatPane() {
    for (const sel of CHAT_PANE_SELECTORS) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  function isMessageNode(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) return false;
    return MESSAGE_NODE_SELECTORS.some((sel) => node.matches?.(sel) || node.querySelector?.(sel));
  }

  function isOutgoing(node) {
    // Heurística: Telegram marca los mensajes propios con clases que contienen
    // "out", "own" o "is-out". Si no se detecta, se asume entrante (más seguro
    // para el propósito de este sistema: solo responder a lo que llega).
    const cls = (node.className || "").toString().toLowerCase();
    return /\b(out|own|is-out)\b/.test(cls);
  }

  function extractBody(node) {
    const candidates = node.querySelectorAll?.(".text-content, .message-text, .text") || [];
    for (const el of candidates) {
      const text = (el.textContent || "").trim();
      if (text) return text;
    }
    return (node.textContent || "").trim();
  }

  function extractExternalId() {
    // El chat activo suele exponer un identificador en la URL o en un atributo
    // del panel. Como fallback, se usa el nombre del chat visible.
    const peer = document.querySelector("[data-peer-id]")?.getAttribute("data-peer-id");
    if (peer) return String(peer);
    const title = document.querySelector(".chat-info .title, .ChatInfo .title, .peer-title");
    return (title?.textContent || "unknown").trim();
  }

  function extractDisplayName() {
    const title = document.querySelector(".chat-info .title, .ChatInfo .title, .peer-title");
    return (title?.textContent || "Desconocido").trim();
  }

  return { findChatPane, isMessageNode, isOutgoing, extractBody, extractExternalId, extractDisplayName };
})();


// Debounce para no disparar una extracción por cada mutación de presencia/typing.
function debounce(fn, ms) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}


// Marca los nodos ya procesados para no reenviarlos tras un re-render suave.
const processed = new WeakSet();


const processMutations = debounce((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (!TelegramAdapter.isMessageNode(node)) continue;
      if (processed.has(node)) continue;
      processed.add(node);

      if (TelegramAdapter.isOutgoing(node)) continue;

      const body = TelegramAdapter.extractBody(node);
      if (!body) continue;

      browser.runtime.sendMessage({
        type: "ingest",
        payload: {
          channel: "telegram_web",
          external_id: TelegramAdapter.extractExternalId(),
          display_name: TelegramAdapter.extractDisplayName(),
          body,
          raw_payload: { source: "telegram_web_dom", snippet: body.slice(0, 200) },
        },
      }).catch((err) => console.warn("[asistente] sendMessage falló:", err));
    }
  }
}, 400);


let currentObserver = null;
let currentPane = null;


function attachObserver() {
  const pane = TelegramAdapter.findChatPane();
  if (!pane) return;

  // Si el panel no ha cambiado, no reenganchar.
  if (pane === currentPane && currentObserver) return;

  if (currentObserver) currentObserver.disconnect();
  currentPane = pane;
  currentObserver = new MutationObserver(processMutations);
  currentObserver.observe(pane, { childList: true, subtree: true });
  console.log("[asistente] observer enganchado al panel de chat");
}


// El cambio de chat es un evento de primera clase: se detecta con un observer
// ligero sobre el título y con un intervalo de respaldo (por si el SPA no
// dispara mutaciones en la cabecera).
const chatSwitchObserver = new MutationObserver(() => {
  // Pequeña espera para que el nuevo panel se monte.
  setTimeout(attachObserver, 300);
});


function start() {
  attachObserver();
  chatSwitchObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
  // Respaldo: si el SPA cambia de chat sin mutación detectable en body.
  setInterval(attachObserver, 3000);
}


if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start);
} else {
  start();
}