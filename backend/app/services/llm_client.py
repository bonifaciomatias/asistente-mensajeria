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


def generate(messages: list[dict]) -> tuple[str, int, int]:
    """
    Devuelve (texto_generado, tokens_in, tokens_out).
    Lanza excepción si Groq falla.
    """
    resp = _get_client().chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.6,
        max_tokens=400,
    )
    text = (resp.choices[0].message.content or "").strip()
    usage = resp.usage
    return text, usage.prompt_tokens, usage.completion_tokens