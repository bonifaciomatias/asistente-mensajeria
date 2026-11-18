from datetime import datetime
from sqlalchemy.orm import Session
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message


def ingest_incoming(
    db: Session,
    *,
    channel: str,
    external_id: str,
    display_name: str,
    body: str,
    raw_payload: dict,
) -> Message:
    contact = (
        db.query(Contact)
        .filter_by(channel=channel, external_id=external_id)
        .first()
    )
    if contact is None:
        contact = Contact(
            channel=channel,
            external_id=external_id,
            display_name=display_name,
        )
        db.add(contact)
        db.flush()
    else:
        contact.last_seen_at = datetime.utcnow()
        if display_name and contact.display_name != display_name:
            contact.display_name = display_name

    conversation = (
        db.query(Conversation)
        .filter_by(contact_id=contact.id, status="open")
        .first()
    )
    if conversation is None:
        conversation = Conversation(
            contact_id=contact.id,
            channel=channel,
            status="open",
        )
        db.add(conversation)
        db.flush()

    now = datetime.utcnow()
    conversation.last_message_at = now

    message = Message(
        conversation_id=conversation.id,
        contact_id=contact.id,
        direction="in",
        body=body,
        raw_payload=raw_payload,
        received_at=now,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message