import re

FORBIDDEN_PHRASES = (
    "como ia", "como modelo", "como inteligencia artificial",
    "soy un asistente virtual", "soy un bot",
)
URL_RE = re.compile(r"https?://\S+")

MIN_LEN = 3
MAX_LEN = 1000


def validate(text: str) -> tuple[bool, str]:
    if not text:
        return False, "empty"
    if len(text) < MIN_LEN:
        return False, "too_short"
    if len(text) > MAX_LEN:
        return False, "too_long"

    low = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in low:
            return False, f"forbidden_phrase:{phrase}"

    # URLs solo permitidas si están en media_catalog (futuro); por ahora, bloqueo total
    if URL_RE.search(text):
        return False, "contains_url"

    return True, "ok"