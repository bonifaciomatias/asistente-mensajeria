import time
import httpx
from app.core.config import settings

MAX_LEN = 4000  # margen bajo el límite de 4096 de Telegram


def _chunk_text(text: str) -> list[str]:
    chunks: list[str] = []
    while text:
        if len(text) <= MAX_LEN:
            chunks.append(text)
            break
        cut = text.rfind("\n", 0, MAX_LEN)
        if cut == -1:
            cut = MAX_LEN
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    return chunks


def send_text(chat_id: str, text: str) -> tuple[bool, str | None]:
    """
    Devuelve (ok, error_msg). ok=True si todos los chunks se enviaron.
    Respeta el límite de ~1 msg/seg por chat.
    """
    token = settings.telegram_bot_token
    if not token:
        return False, "TELEGRAM_BOT_TOKEN vacío"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = _chunk_text(text)

    for i, chunk in enumerate(chunks):
        sent = False
        for attempt in range(3):
            try:
                r = httpx.post(
                    url,
                    json={
                        "chat_id": chat_id,
                        "text": chunk,
                        "disable_web_page_preview": True,
                    },
                    timeout=10.0,
                )
                data = r.json()
                if data.get("ok"):
                    sent = True
                    break
                if r.status_code == 429:
                    retry = data.get("parameters", {}).get("retry_after", 5)
                    print(f"[sender] 429, esperando {retry}s")
                    time.sleep(retry)
                    continue
                # Error permanente (chat bloqueado, texto inválido, etc.)
                return False, f"telegram_error:{data.get('description', data)}"
            except Exception as exc:
                print(f"[sender] intento {attempt+1} falló: {exc}")
                time.sleep(2)

        if not sent:
            return False, f"chunk_{i}_failed_after_retries"

        # Rate limit: ~1 msg/seg por chat
        if i < len(chunks) - 1:
            time.sleep(1.0)

    return True, None