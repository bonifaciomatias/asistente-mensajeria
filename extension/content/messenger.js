// ============================================================
// Adaptador del DOM de Messenger (Lexical / React)
// ============================================================
const MessengerAdapter = (() => {
  function findMainPane() {
    return document.querySelector('[role="main"]');
  }

  function findEditor() {
    const el = document.querySelector('div[contenteditable="true"][role="textbox"]');
    return el && el.isConnected ? el : null;
  }

  function listSidebarChats() {
    return Array.from(document.querySelectorAll('a[href^="/t/"]')).filter(a => {
      const href = a.getAttribute("href");
      return href && href !== "/t/";
    });
  }

  function hasUnreadBadge(chatEl) {
    const aria = (chatEl.getAttribute("aria-label") || "").toLowerCase();
    if (aria.includes("unread") || aria.includes("no leído") || aria.includes("no leídas")) return true;

    const spans = chatEl.querySelectorAll('span');
    for (const s of spans) {
      if (s.offsetParent === null) continue;
      const txt = s.innerText.trim();
      if (/^\d+$/.test(txt)) return true;
      const sAria = (s.getAttribute("aria-label") || "").toLowerCase();
      if (sAria.includes("unread") || sAria.includes("no leído")) return true;
    }
    return false;
  }

  function getChatIdFromSidebarItem(chatEl) {
    const href = chatEl.getAttribute("href") || "";
    const match = href.match(/\/t\/([^/?#]+)/);
    return match ? match[1] : "";
  }

  function getChatNameFromSidebarItem(chatEl) {
    const label = chatEl.getAttribute("aria-label") || "";
    // El label suele ser "Mario Santibañez, 1 no leídas"
    const parts = label.split(",");
    if (parts.length > 0 && parts[0].trim() !== "Chats · 1 no leídas") {
      return parts[0].trim();
    }
    return "Contacto";
  }

  function getActiveChatId() {
    const active = document.querySelector('a[href^="/t/"][aria-current="page"]');
    if (active) {
      const id = getChatIdFromSidebarItem(active);
      if (id) return id;
    }
    return "";
  }

  function getLatestIncomingBlock() {
    const pane = findMainPane();
    if (!pane) return "";
    
    // Buscamos todos los textos dir="auto", excluyendo encabezados (h2) e inputs
    const textEls = Array.from(pane.querySelectorAll('[dir="auto"]')).filter(el => {
      if (el.tagName === 'H2' || el.closest('h2')) return false;
      const txt = el.innerText.trim();
      if (!txt || txt === "Aa" || txt.includes("Escribe a") || txt.includes("Presiona Enter")) return false;
      return true;
    });

    if (textEls.length === 0) return "";

    const paneRect = pane.getBoundingClientRect();
    const valid = [];
    
    for (const el of textEls) {
      const txt = el.innerText.trim();
      const rect = el.getBoundingClientRect();
      
      // Ignorar elementos fuera del área visible
      if (rect.bottom < paneRect.top || rect.top > paneRect.bottom) continue;

      // Determinar si es saliente por posición (mitad derecha del panel)
      const isOut = (rect.left + rect.width / 2) > (paneRect.left + paneRect.width / 2);
      valid.push({ text: txt, isOut });
    }
    
    if (valid.length === 0) return "";

    // Agrupar entrantes consecutivos al final
    let block = [];
    for (let i = valid.length - 1; i >= 0; i--) {
      if (valid[i].isOut) break;
      block.unshift(valid[i].text);
    }
    return block.join("\n").trim();
  }

  return {
    findMainPane, findEditor, listSidebarChats, hasUnreadBadge,
    getChatIdFromSidebarItem, getChatNameFromSidebarItem,
    getActiveChatId, getLatestIncomingBlock
  };
})();


// ============================================================
// Navegación (abrir chat, esperar, liberar foco)
// ============================================================
const MessengerNavigator = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function openChat(chatEl) {
    chatEl.click();
  }

  async function waitForActiveChat(expectedId) {
    await sleep(250);
    for (let i = 0; i < 20; i++) {
      const activeId = MessengerAdapter.getActiveChatId();
      const pane = MessengerAdapter.findMainPane();
      if (pane && pane.querySelector('[dir="auto"]')) {
        if (!expectedId || !activeId || activeId === expectedId) return pane;
      }
      await sleep(150);
    }
    return MessengerAdapter.findMainPane();
  }

  async function releaseFocus() {
    const fireEsc = (el) => {
      if (!el) return;
      const ev = { key: "Escape", code: "Escape", keyCode: 27, which: 27, bubbles: true, cancelable: true };
      el.dispatchEvent(new KeyboardEvent("keydown", ev));
    };
    const editor = MessengerAdapter.findEditor();
    if (editor) { fireEsc(editor); await sleep(200); }
    fireEsc(document.body);
    await sleep(200);
    if (document.activeElement?.blur) document.activeElement.blur();
    await sleep(300);
  }

  return { openChat, waitForActiveChat, releaseFocus };
})();


// ============================================================
// Envío con xdotool
// ============================================================
const MessengerSender = (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function sendDraft(draft) {
    const editor = MessengerAdapter.findEditor();
    if (!editor) {
      await browser.runtime.sendMessage({ type: "confirm_failed", draftId: draft.id, reason: "no_editor_found" });
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
      await browser.runtime.sendMessage({
        type: "confirm_failed", draftId: draft.id, reason: writeResp?.result?.error || "write_failed",
      });
      return;
    }

    await sleep(800);
    await browser.runtime.sendMessage({ type: "confirm_sent", draftId: draft.id, text: draft.body });
  }

  return { sendDraft };
})();


// ============================================================
// Detección de operador
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
  const editor = MessengerAdapter.findEditor();
  if (editor && (editor.innerText || "").trim().length > 0 && now - lastKeyActivity < 30000) return true;
  return false;
}


// ============================================================
// Bucle de escaneo
// ============================================================
const COOLDOWN_MS = 15000;
const POLL_MS = 2000;

let processing = false;
const lastProcessed = new Map();
const seenHashes = new Map();
const initializedChats = new Set(); // Para ignorar el historial al abrir un chat

function hashText(t) {
  let h = 0;
  for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) | 0;
  return String(h);
}

function pickNextUnreadChat() {
  const now = Date.now();

  // Capa 1: Chats con badge de no leídos
  for (const chatEl of MessengerAdapter.listSidebarChats()) {
    if (!MessengerAdapter.hasUnreadBadge(chatEl)) continue;
    const id = MessengerAdapter.getChatIdFromSidebarItem(chatEl);
    if (!id) continue;
    const last = lastProcessed.get(id) || 0;
    if (now - last < COOLDOWN_MS) continue;
    
    initializedChats.add(id); // Evitar que Capa 2 lo procese de nuevo por error
    return { chatEl, id, name: MessengerAdapter.getChatNameFromSidebarItem(chatEl) };
  }

  // Capa 2: Chat activo con mensajes nuevos
  const activeId = MessengerAdapter.getActiveChatId();
  if (!activeId) return null;

  // Si es la primera vez que vemos este chat en esta sesión, guardamos su estado y NO lo procesamos
  if (!initializedChats.has(activeId)) {
    initializedChats.add(activeId);
    const initialIncoming = MessengerAdapter.getLatestIncomingBlock();
    if (initialIncoming) {
      seenHashes.set(activeId, hashText(initialIncoming));
    }
    console.log(`[messenger] Chat ${activeId} inicializado (ignorando historial)`);
    return null;
  }

  const last = lastProcessed.get(activeId) || 0;
  if (now - last < COOLDOWN_MS) return null;

  const incoming = MessengerAdapter.getLatestIncomingBlock();
  if (!incoming) return null;
  const h = hashText(incoming);
  if (seenHashes.get(activeId) === h) return null;

  for (const chatEl of MessengerAdapter.listSidebarChats()) {
    if (MessengerAdapter.getChatIdFromSidebarItem(chatEl) === activeId) {
      return { chatEl, id: activeId, name: MessengerAdapter.getChatNameFromSidebarItem(chatEl) };
    }
  }
  return null;
}

async function processChat({ chatEl, id, name }) {
  console.log(`[messenger] procesando ${id} (${name})`);
  MessengerNavigator.openChat(chatEl);
  const pane = await MessengerNavigator.waitForActiveChat(id);
  if (!pane) {
    lastProcessed.set(id, Date.now());
    return;
  }

  const incoming = MessengerAdapter.getLatestIncomingBlock();
  if (!incoming) {
    console.log(`[messenger] ${id} sin mensaje entrante legible`);
    lastProcessed.set(id, Date.now());
    await MessengerNavigator.releaseFocus();
    return;
  }

  const h = hashText(incoming);
  if (seenHashes.get(id) === h) {
    lastProcessed.set(id, Date.now());
    await MessengerNavigator.releaseFocus();
    return;
  }
  seenHashes.set(id, h);

  try {
    const result = await browser.runtime.sendMessage({
      type: "ingest",
      payload: {
        channel: "messenger",
        external_id: id,
        display_name: name,
        body: incoming,
        raw_payload: { source: "messenger_dom", chat_id: id, snippet: incoming.slice(0, 200) },
      },
    });

    if (!result?.ok) return;
    const { decision, draft } = result.result || {};
    console.log(`[messenger] ${id} → ${decision}`);

    if (decision === "auto_send" && draft && draft.status === "generated") {
      await MessengerSender.sendDraft(draft);
    }
  } catch (err) {
    console.warn(`[messenger] error ${id}:`, err);
  } finally {
    const after = MessengerAdapter.getLatestIncomingBlock();
    const hashAfter = hashText(after);
    const hasNew = after.length > 0 && hashAfter !== h;

    if (hasNew) {
      console.log(`[messenger] nuevos mensajes en ${id}, manteniendo abierto`);
      lastProcessed.delete(id);
    } else {
      lastProcessed.set(id, Date.now());
      await MessengerNavigator.releaseFocus();
    }
  }
}

async function scanInbox() {
  if (processing) return;
  if (operatorIsBusy()) return;

  const next = pickNextUnreadChat();
  if (!next) return;

  processing = true;
  try {
    await processChat(next);
  } catch (err) {
    console.error("[messenger] processChat error:", err);
  } finally {
    setTimeout(() => { processing = false; }, 2000);
  }
}

setInterval(scanInbox, POLL_MS);
console.log("[messenger] content script Messenger iniciado");