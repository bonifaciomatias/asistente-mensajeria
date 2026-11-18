from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm_client import _get_client


SUMMARY_SYSTEM = (
    "Eres un asistente que condensa historiales de conversación para preservar contexto. "
    "Se te entrega: (1) un resumen previo si existe, (2) mensajes nuevos. "
    "Genera un resumen actualizado que preserve: identidad y preferencias del contacto, "
    "temas tratados, compromisos pendientes, y datos relevantes para continuar la conversación. "
    f"Sé conciso (máximo ~{settings.summary_target_tokens} tokens). No inventes datos. "
    "No incluyas saludos, meta-comentarios ni firmas. Responde solo con el resumen."
)


def _live_messages(db: Session, conv: Conversation) -> list[Message]:
    q = db.query(Message).filter(
        Message.conversation_id == conv.id,
        Message.body.isnot(None),
        (Message.direction == "in") | (Message.send_status == "sent"),
    )
    if conv.summary_last_message_id:
        q = q.filter(Message.id > conv.summary_last_message_id)
    return q.order_by(Message.id.asc()).all()


def should_summarize(db: Session, conv: Conversation) -> bool:
    msgs = _live_messages(db, conv)
    total_chars = sum(len(m.body or "") for m in msgs)
    return (total_chars / 4) > settings.summarize_threshold_tokens


def summarize(db: Session, conv: Conversation) -> bool:
    msgs = _live_messages(db, conv)
    if not msgs:
        return False

    lines = []
    for m in msgs:
        who = "Contacto" if m.direction == "in" else "Asistente"
        lines.append(f"{who}: {m.body}")
    new_block = "\n".join(lines)

    prev_block = conv.summary or "(sin resumen previo)"
    user_content = (
        f"RESUMEN PREVIO:\n{prev_block}\n\n"
        f"MENSAJES NUEVOS:\n{new_block}\n\n"
        "Genera el resumen actualizado."
    )

    try:
        resp = _get_client().chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=settings.summary_target_tokens,
        )
        summary = (resp.choices[0].message.content or "").strip()
        if not summary:
            return False
    except Exception as exc:
        print(f"[summarizer] error: {exc}")
        return False

    conv.summary = summary
    conv.summary_tokens = resp.usage.completion_tokens
    conv.summary_updated_at = datetime.utcnow()
    conv.summary_last_message_id = msgs[-1].id
    db.commit()
    print(
        f"[summarizer] conv={conv.id} nuevo resumen "
        f"({conv.summary_tokens} tok, cubre hasta msg={conv.summary_last_message_id})"
    )
    return True