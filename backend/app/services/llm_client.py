from groq import Groq
from app.core.config import settings

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY vacío en .env")
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def _clean(raw: str | None) -> str:
    if not raw:
        return ""
    text = raw.strip()
    # Quitar thinking tags si vienen en content
    import re
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</?think>", "", text, flags=re.IGNORECASE)
    # Quitar prefijos tipo "Asistente:" o "Silvia:"
    text = re.sub(r"^(Asistente|Assistant|IA|Silvia):\s*", "", text, flags=re.IGNORECASE)
    # Quitar comillas envolventes
    if len(text) > 2 and (
        (text.startswith('"') and text.endswith('"'))
        or (text.startswith("'") and text.endswith("'"))
    ):
        text = text[1:-1].strip()
    return text


def _attempt(payload: dict) -> str:
    resp = _get_client().chat.completions.create(**payload)
    choice = resp.choices[0]
    text = _clean(choice.message.content)
    if not text:
        raise RuntimeError(f"RESPUESTA_VACIA:finish={choice.finish_reason}")
    return text, resp.usage.prompt_tokens, resp.usage.completion_tokens


def generate(messages: list[dict]) -> tuple[str, int, int]:
    """
    Genera texto con Qwen 3.8. Devuelve (texto, tokens_in, tokens_out).
    Aplica tres intentos progresivos para sortear el 'stop vacío' de Qwen 3.8.
    """
    base = {
        "model": settings.groq_model,
        "messages": messages,
    }

    # Intento 1: reasoning_effort="none" (rápido, el que menos tokens gasta)
    try:
        return _attempt({
            **base,
            "temperature": 0.7,
            "top_p": 0.8,
            "frequency_penalty": 0.3,
            "max_completion_tokens": 600,
            "reasoning_effort": "none",
            "stream": False,
        })
    except RuntimeError as e:
        if "RESPUESTA_VACIA" not in str(e):
            raise

    # Intento 2: reasoning_effort="low" + reasoning_format="parsed"
    try:
        return _attempt({
            **base,
            "temperature": 0.8,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "max_completion_tokens": 1024,
            "reasoning_effort": "low",
            "reasoning_format": "parsed",
            "stream": False,
        })
    except RuntimeError as e:
        if "RESPUESTA_VACIA" not in str(e):
            raise

    # Intento 3: sin historial (solo system + último user)
    trimmed = [messages[0]] + [messages[-1]] if len(messages) > 2 else messages
    return _attempt({
        "model": settings.groq_model,
        "messages": trimmed,
        "temperature": 0.8,
        "top_p": 0.9,
        "frequency_penalty": 0.3,
        "max_completion_tokens": 1024,
        "reasoning_effort": "low",
        "reasoning_format": "parsed",
        "stream": False,
    })