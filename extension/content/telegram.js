// ============================================================
// Adaptador del DOM de Telegram Web (WebK)
// ============================================================
const TelegramAdapter = (() => {
  const CHAT_PANE_SELECTORS = [
    "#column-center .chat.active .bubbles",
    "#column-center .chat.active .messages-layout",
    ".chat-container .bubbles",
    "#column-center .bubbles",
  ];

  function findChatPane() {
    for (const sel of CHAT_PANE_SELECTORS) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  function findEditor() {
    const sels = [
      '.input-message-input[contenteditable="true"]',
      '.form-control[contenteditable="true"]',
      '.chat-input [contenteditable="true"]',
      '[contenteditable="true"][data-placeholder]',
    ];
    for (const sel of sels) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  function findActiveChat() {
    return (
      document.querySelector("#column-center .chat.active") ||
      document.querySelector(".chats-container .chat.active") ||
      document.querySelector(".chat.active")
    );
  }

  function listSidebarChats() {
    return document.querySelectorAll(
      "#chatlist-container .chatlist-chat, .chatlist .chatlist-chat, .chatlist-chat"
    );
  }

  function hasUnreadBadge(chatEl) {
    const badges = chatEl.querySelectorAll(
      ".dialog-subtitle-badge.unread, .unread:not(.unread-reaction), .badge, .chat-badge"
    );
    for (const b of badges) {
      if (b.offsetParent === null) continue;
      const txt = (b.innerText || "").trim();
      if (txt !== "" && txt !== "0") return true;
      if (b.classList.contains("unread") && b.classList.contains("is-visible")) return true;
    }
    return false;
  }

  function getChatIdFromSidebarItem(chatEl) {
    const raw =
      chatEl.getAttribute("data-peer-id") ||
      chatEl.getAttribute("href") ||
      (chatEl.innerText || "").slice(0, 20);
    return String(raw || "").trim().replace(/^#/, "");
  }

  function getChatNameFromSidebarItem(chatEl) {
    const nameEl = chatEl.querySelector(
      ".row-title .peer-title, .dialog-title, .peer-title, .title"
    );
    return nameEl ? nameEl.innerText.trim() : "Amigo";
  }

  function getActiveChatId() {
    const chat = findActiveChat();
    if (!chat) return "";
    const raw =
      chat.getAttribute("data-peer-id") ||
      chat.querySelector("[data-peer-id]")?.getAttribute("data-peer-id") ||
      window.location.hash ||
      "";
    return String(raw).trim().replace(/^#/, "");
  }

  function isOutgoing(bubble) {
    return bubble.classList.contains("is-out");
  }

  function extractBubbleContent(bubble) {
    if (!bubble) return "";

    const textNode = bubble.querySelector(".translatable-message, .text-content");
    if (textNode && textNode.innerText.trim()) return textNode.innerText.trim();

    const msg = bubble.querySelector(".message");
    if (msg) {
      const clone = msg.cloneNode(true);
      clone
        .querySelectorAll(
          ".time, .reply, .reactions, .message-signature, .peer-title, .document-wrapper"
        )
        .forEach((el) => el.remove());
      const text = clone.innerText.trim();
      if (text) return text;
    }

    if (bubble.querySelector(".sticker, .media-sticker-wrapper")) return "[Sticker]";
    if (bubble.querySelector(".audio-wrapper, audio-element, .voice-message"))
      return "[Nota de voz]";
    if (bubble.querySelector(".media-video, video")) return "[Video o GIF]";
    if (bubble.querySelector(".media-photo, img.thumbnail")) return "[Foto]";
    if (bubble.querySelector(".document-wrapper")) return "[Archivo]";
    return "";
  }

  // CAMBIO: busca el último bloque de mensajes entrantes aunque haya
  // respuestas del bot (out) después. Antes, si el último bubble era out,
  // devolvía "" y los mensajes que llegaron durante el tecleo se perdían.
  function getLatestIncomingBlock() {
    const pane = findChatPane();
    if (!pane) return "";

    const bubbles = Array.from(pane.querySelectorAll(".bubble:not(.service)"));
    if (bubbles.length === 0) return "";

    // Encontrar el índice del último mensaje ENTRANTE (ignorando outs al final)
    let lastInIdx = -1;
    for (let i = bubbles.length - 1; i >= 0; i--) {
      if (!isOutgoing(bubbles[i])) {
        lastInIdx = i;
        break;
      }
    }
    if (lastInIdx === -1) return "";

    // Agrupar entrantes consecutivos hacia atrás desde lastInIdx
    const incoming = [];
    for (let i = lastInIdx; i >= 0 && incoming.length < 5; i--) {
      const b = bubbles[i];
      if (isOutgoing(b)) break;
      const content = extractBubbleContent(b);
      if (content) incoming.unshift(content);
    }
    return incoming.join("\n").trim();
  }

  return {
    findChatPane,
    findEditor,
    findActiveChat,
    listSidebarChats,
    hasUnreadBadge,
    getChatIdFromSidebarItem,
    getChatNameFromSidebarItem,
    getActiveChatId,
    getLatestIncomingBlock,
    isOutgoing,
    extractBubbleContent,
  };
})();


// ============================================================
// Navegación de chats (abrir, esperar, liberar foco)
// ============================================================
const ChatNavigator = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function openChat(chatEl) {
    const opts = { bubbles: true, cancelable: true };
    chatEl.dispatchEvent(new MouseEvent("mousedown", opts));
    chatEl.dispatchEvent(new MouseEvent("mouseup", opts));
    chatEl.dispatchEvent(new MouseEvent("click", opts));
    chatEl.click();

    const href = chatEl.getAttribute("href");
    if (href && href.startsWith("#") && window.location.hash !== href) {
      window.location.hash = href;
    }
  }

  async function waitForActiveChat(expectedId) {
    const idNorm = String(expectedId || "").trim().replace(/^#/, "");
    await sleep(250);

    for (let i = 0; i < 20; i++) {
      const active = TelegramAdapter.findActiveChat();
      if (active) {
        const peerId = TelegramAdapter.getActiveChatId();
        const hasBubbles = active.querySelector(".bubble");
        if (!idNorm || !peerId || peerId === idNorm || hasBubbles) {
          if (hasBubbles || TelegramAdapter.findChatPane()) {
            return active;
          }
        }
      }
      await sleep(150);
    }
    return TelegramAdapter.findActiveChat();
  }

  async function releaseFocus() {
    const fireEscape = (elem) => {
      if (!elem) return;
      const ev = {
        key: "Escape",
        code: "Escape",
        keyCode: 27,
        which: 27,
        bubbles: true,
        cancelable: true,
      };
      elem.dispatchEvent(new KeyboardEvent("keydown", ev));
    };

    const editor = TelegramAdapter.findEditor();
    if (editor) {
      fireEscape(editor);
      document.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "Escape",
          code: "Escape",
          keyCode: 27,
          which: 27,
          bubbles: true,
          cancelable: true,
        })
      );
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: "Escape",
          code: "Escape",
          keyCode: 27,
          which: 27,
          bubbles: true,
          cancelable: true,
        })
      );
      await sleep(200);
    }

    fireEscape(document.body);
    await sleep(200);

    if (document.activeElement?.blur) {
      document.activeElement.blur();
    }
    await sleep(300);

    if (TelegramAdapter.findActiveChat() && window.location.hash) {
      console.log("[asistente] chat sigue activo, deseleccionando con hash vacío");
      window.location.hash = "#";
      await sleep(400);
    }
  }

  return { openChat, waitForActiveChat, releaseFocus };
})();


// ============================================================
// Envío con xdotool + confirmación por DOM
// ============================================================
const TelegramSender = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function waitForOutgoingMessage(expectedText, timeoutMs = 8000) {
    return new Promise((resolve, reject) => {
      const pane = TelegramAdapter.findChatPane();
      if (!pane) return reject(new Error("no_chat_pane"));

      const needle = (expectedText || "").slice(0, 30);
      const start = Date.now();

      const check = () => {
        const bubbles = Array.from(pane.querySelectorAll(".bubble.is-out"));
        for (let i = bubbles.length - 1; i >= 0; i--) {
          const text = (bubbles[i].innerText || "").trim();
          if (text.includes(needle)) return true;
        }
        return false;
      };

      const observer = new MutationObserver(() => {
        if (check()) {
          observer.disconnect();
          resolve(true);
        }
      });
      observer.observe(pane, { childList: true, subtree: true });

      const timer = setInterval(() => {
        if (check()) {
          clearInterval(timer);
          observer.disconnect();
          resolve(true);
        } else if (Date.now() - start > timeoutMs) {
          clearInterval(timer);
          observer.disconnect();
          reject(new Error("confirmation_timeout"));
        }
      }, 300);
    });
  }

  // CAMBIO: sendDraft ya NO cierra el chat. Solo teclea, espera 800ms,
  // y confirma el envío por DOM (best-effort). El cierre lo decide
  // processChat, que sabe si llegaron mensajes nuevos durante el tecleo.
  async function sendDraft(draft) {
    const editor = TelegramAdapter.findEditor();
    if (!editor) {
      await browser.runtime.sendMessage({
        type: "confirm_failed",
        draftId: draft.id,
        reason: "no_editor_found",
      });
      return;
    }

    editor.focus();
    editor.click();
    await sleep(250);

    const writeResp = await browser.runtime.sendMessage({
      type: "write",
      payload: { text: draft.body, draft_id: draft.id, press_enter: true },
    });

    if (!writeResp?.ok || !writeResp?.result?.ok) {
      const reason = writeResp?.result?.error || writeResp?.error || "write_failed";
      await browser.runtime.sendMessage({
        type: "confirm_failed",
        draftId: draft.id,
        reason,
      });
      return;
    }

    await sleep(800);

    try {
      await waitForOutgoingMessage(draft.body, 2000);
    } catch (_) {
      // xdotool ya pulsó Enter; si la confirmación DOM falla, asumimos enviado.
    }
    await browser.runtime.sendMessage({
      type: "confirm_sent",
      draftId: draft.id,
      text: draft.body,
    });
  }

  return { sendDraft };
})();


// ============================================================
// Detección de actividad del operador
// ============================================================
let lastKeyActivity = 0;
let lastScrollActivity = 0;

document.addEventListener("keydown", () => { lastKeyActivity = Date.now(); }, true);
document.addEventListener("input", () => { lastKeyActivity = Date.now(); }, true);
document.addEventListener("scroll", () => { lastScrollActivity = Date.now(); }, true);

function operatorIsBusy() {
  const now = Date.now();
  if (now - lastKeyActivity < 5000) return true;
  if (now - lastScrollActivity < 3000) return true;

  const editor = TelegramAdapter.findEditor();
  if (
    editor &&
    (editor.innerText || "").trim().length > 0 &&
    now - lastKeyActivity < 30000
  ) {
    return true;
  }
  return false;
}


// ============================================================
// Bucle principal: escaneo de bandeja + procesamiento en serie
// ============================================================
const COOLDOWN_MS = 15000;
const SIDEBAR_POLL_MS = 1500;

let processing = false;
const lastProcessed = new Map();
const seenMessageHashes = new Map();


// Caché del estado horario (evita consultar el backend en cada tick)
let businessHoursCache = { value: null, ts: 0 };
const HOURS_CACHE_MS = 60000;  // refrescar cada 60s

async function isInBusinessHours() {
  const now = Date.now();
  if (businessHoursCache.value !== null && now - businessHoursCache.ts < HOURS_CACHE_MS) {
    return businessHoursCache.value;
  }
  try {
    const resp = await browser.runtime.sendMessage({ type: "get_status" });
    if (resp?.ok && resp.result) {
      businessHoursCache = { value: resp.result.in_business_hours, ts: now };
      return resp.result.in_business_hours;
    }
  } catch (err) {
    console.warn("[asistente] no se pudo consultar /status:", err);
  }
  // Si falla la consulta, asumir fuera de horario (conservador: no abrir chats)
  return false;
}

function hashText(text) {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
  return String(h);
}

function pickNextUnreadChat() {
  const now = Date.now();

  // 1. Chats con badge de no leídos (vía principal)
  for (const chatEl of TelegramAdapter.listSidebarChats()) {
    if (!TelegramAdapter.hasUnreadBadge(chatEl)) continue;
    const id = TelegramAdapter.getChatIdFromSidebarItem(chatEl);
    if (!id) continue;
    const last = lastProcessed.get(id) || 0;
    if (now - last < COOLDOWN_MS) continue;
    return { chatEl, id, name: TelegramAdapter.getChatNameFromSidebarItem(chatEl) };
  }

  // 2. Red de seguridad: chat activo con mensajes nuevos (aunque no
  //    muestre badge porque está seleccionado). Cubre el caso de mensajes
  //    que llegan mientras el bot teclea.
  const activeChat = TelegramAdapter.findActiveChat();
  if (!activeChat) return null;

  const activeId = TelegramAdapter.getActiveChatId();
  if (!activeId) return null;

  const last = lastProcessed.get(activeId) || 0;
  if (now - last < COOLDOWN_MS) return null;

  const incoming = TelegramAdapter.getLatestIncomingBlock();
  if (!incoming) return null;

  const h = hashText(incoming);
  if (seenMessageHashes.get(activeId) === h) return null;

  for (const chatEl of TelegramAdapter.listSidebarChats()) {
    const id = TelegramAdapter.getChatIdFromSidebarItem(chatEl);
    if (id === activeId) {
      return {
        chatEl,
        id: activeId,
        name: TelegramAdapter.getChatNameFromSidebarItem(chatEl),
      };
    }
  }
  return null;
}

async function processChat({ chatEl, id, name }) {
  console.log(`[asistente] procesando chat ${id} (${name})`);

  ChatNavigator.openChat(chatEl);
  const active = await ChatNavigator.waitForActiveChat(id);
  if (!active) {
    console.warn(`[asistente] chat ${id} no llegó a abrir`);
    lastProcessed.set(id, Date.now());
    return;
  }

  const incoming = TelegramAdapter.getLatestIncomingBlock();
  if (!incoming) {
    console.log(`[asistente] chat ${id} sin mensaje entrante`);
    lastProcessed.set(id, Date.now());
    await ChatNavigator.releaseFocus();
    return;
  }

  const h = hashText(incoming);
  if (seenMessageHashes.get(id) === h) {
    console.log(`[asistente] chat ${id} sin mensaje nuevo (hash igual)`);
    lastProcessed.set(id, Date.now());
    await ChatNavigator.releaseFocus();
    return;
  }
  seenMessageHashes.set(id, h);

  try {
    const result = await browser.runtime.sendMessage({
      type: "ingest",
      payload: {
        channel: "telegram_web",
        external_id: id,
        display_name: name,
        body: incoming,
        raw_payload: {
          source: "telegram_web_dom",
          chat_id: id,
          snippet: incoming.slice(0, 200),
        },
      },
    });

    if (!result?.ok) {
      console.warn(`[asistente] ingest falló para ${id}:`, result?.reason);
      return;
    }

    const { decision, draft } = result.result || {};
    console.log(`[asistente] chat ${id} → ${decision}`);

    if (decision === "auto_send" && draft && draft.status === "generated") {
      await TelegramSender.sendDraft(draft);
    }
  } catch (err) {
    console.warn(`[asistente] error procesando ${id}:`, err);
  } finally {
    // CAMBIO: verificar si llegaron mensajes nuevos durante el procesamiento.
    // Si el hash del bloque entrante cambió, mantener el chat abierto y no
    // aplicar cooldown. El siguiente tick de scanInbox procesará el bloque
    // actualizado vía capa 2 de pickNextUnreadChat.
    const incomingAfter = TelegramAdapter.getLatestIncomingBlock();
    const hashAfter = hashText(incomingAfter);
    const hasNewMessages = incomingAfter.length > 0 && hashAfter !== h;

    if (hasNewMessages) {
      console.log(
        `[asistente] nuevos mensajes en ${id} durante procesamiento, manteniendo chat abierto`
      );
      lastProcessed.delete(id);
    } else {
      lastProcessed.set(id, Date.now());
      await ChatNavigator.releaseFocus();
    }
  }
}

async function scanInbox() {
  if (processing) return;

  if (operatorIsBusy()) {
    console.log("[asistente] operador activo, postergando");
    return;
  }

  // NUEVO: consultar horario antes de abrir ningún chat.
  // Si está fuera de horario, no se toca la lista de chats: los mensajes
  // se quedan con badge de no leídos.
  const inHours = await isInBusinessHours();
  if (!inHours) {
    return;  // silencio total: no abrir, no leer, no responder
  }

  const next = pickNextUnreadChat();
  if (!next) return;

  processing = true;
  try {
    await processChat(next);
  } catch (err) {
    console.error("[asistente] processChat error:", err);
  } finally {
    setTimeout(() => {
      processing = false;
    }, 2000);
  }
}

setInterval(scanInbox, SIDEBAR_POLL_MS);
console.log("[asistente] content script Telegram Web (bandeja + operador + deselección) iniciado");