import random
import re
import subprocess
import time

from app.core.config import settings


def normalize_for_xdotool(text: str) -> str:
    """Normaliza texto para que xdotool pueda teclearlo sin problemas."""
    text = (text or "")
    text = re.sub(r"[“”]", '"', text)
    text = re.sub(r"[‘’]", "'", text)
    text = re.sub(r"[—–]", "-", text)
    text = text.replace("…", "...")
    # Emojis fuera del BMP: xdotool no los teclea como teclas físicas
    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)
    text = re.sub(r"\s+\n", "\n", text)
    return text.strip()


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=15)


def _active_window_info() -> tuple[str, str]:
    wid = _run(["xdotool", "getactivewindow"]).stdout.strip()
    if not wid:
        return "", ""
    name = _run(["xdotool", "getwindowname", wid]).stdout.strip()
    return wid, name


def _focus_ok() -> tuple[bool, str]:
    wid, name = _active_window_info()
    if not wid:
        return False, "no_active_window"
    if settings.xdotool_window_keyword.lower() not in name.lower():
        return False, f"unexpected_window:{name[:80]}"
    return True, "ok"


def _chunk(text: str) -> list[str]:
    lo, hi = settings.xdotool_chunk_chars
    chunks: list[str] = []
    i = 0
    while i < len(text):
        size = random.randint(lo, hi)
        chunks.append(text[i : i + size])
        i += size
    return chunks


def _type_chunk(chunk: str) -> bool:
    d_lo, d_hi = settings.xdotool_char_delay_ms
    delay_ms = random.randint(d_lo, d_hi)
    r = _run(["xdotool", "type", "--delay", str(delay_ms), "--", chunk])
    return r.returncode == 0


def write_to_active_window(
    text: str, *, press_enter: bool = True
) -> tuple[bool, str | None]:
    if not text:
        return False, "empty_text"

    text = normalize_for_xdotool(text)
    if not text:
        text = ":)"

    ok, reason = _focus_ok()
    if not ok:
        return False, reason

    for chunk in _chunk(text):
        if not _type_chunk(chunk):
            return False, "xdotool_type_failed"
        lo, hi = settings.xdotool_chunk_pause_s
        time.sleep(random.uniform(lo, hi))

    if press_enter:
        time.sleep(settings.xdotool_enter_grace_s)
        ok, reason = _focus_ok()
        if not ok:
            return False, f"lost_focus_before_enter:{reason}"
        if _run(["xdotool", "key", "Return"]).returncode != 0:
            return False, "xdotool_enter_failed"

    return True, None