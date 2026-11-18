from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.message import Message
from app.core.config import settings


def build_messages(db: Session, conversation: Conversation, system_prompt: str) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]

    if conversation.summary:
        messages.append({
            "role": "system",
            "content": "Resumen de la conversación previa:\n" + conversation.summary,
        })

    q = db.query(Message).filter(
        Message.conversation_id == conversation.id,
        Message.body.isnot(None),
        (Message.direction == "in") | (Message.send_status == "sent"),
    )
    if conversation.summary_last_message_id:
        q = q.filter(Message.id > conversation.summary_last_message_id)

    history = q.order_by(Message.id.asc()).all()

    max_chars = settings.max_context_tokens * 4
    selected: list[Message] = []
    total = 0
    for m in reversed(history):
        total += len(m.body or "")
        if total > max_chars:
            break
        selected.append(m)
    selected.reverse()

    for m in selected:
        role = "user" if m.direction == "in" else "assistant"
        messages.append({"role": role, "content": m.body})
    return messages