from datetime import datetime
from sqlalchemy.orm import Session
from app.models.contact import Contact
from app.models.message import Message
from app.services.context_builder import build_messages
from app.services.llm_client import generate
from app.services.prompt_selector import select_prompt
from app.services.validator import validate
from app.models.conversation import Conversation
from app.services.summarizer import should_summarize, summarize


def generate_draft(db: Session, incoming: Message) -> Message | None:
    contact = db.get(Contact, incoming.contact_id)
    conversation = db.get(Conversation, incoming.conversation_id)

    if should_summarize(db, conversation):
        summarize(db, conversation)

    prompt_obj, system_prompt = select_prompt(db, contact)
    msgs = build_messages(db, conversation, system_prompt)
    text, tok_in, tok_out = generate(msgs)

    ok, reason = validate(text)

    from app.core.config import settings as _s
    draft = Message(
        conversation_id=incoming.conversation_id,
        contact_id=incoming.contact_id,
        direction="out",
        body=text,
        prompt_id_used=prompt_obj.id if prompt_obj else None,
        model_used="groq:" + _s.groq_model,
        tokens_in=tok_in,
        tokens_out=tok_out,
        draft_status="generated" if ok else "rejected",
        send_status=None,
        policy_reason=None if ok else f"validator:{reason}",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft