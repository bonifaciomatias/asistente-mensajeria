import sys
from app.core.db import SessionLocal
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.policy import PolicyLog, RateState, HumanOverride
from app.models.tag import ContactTag


def reset_contact(external_id: str, channel: str = "messenger"):
    with SessionLocal() as db:
        contact = db.query(Contact).filter_by(
            external_id=external_id, channel=channel
        ).first()
        if not contact:
            print(f"No existe contacto {external_id} en {channel}")
            return
        cid = contact.id
        db.query(PolicyLog).filter_by(contact_id=cid).delete()
        db.query(RateState).filter_by(contact_id=cid).delete()
        db.query(HumanOverride).filter_by(contact_id=cid).delete()
        db.query(ContactTag).filter_by(contact_id=cid).delete()
        db.query(Message).filter_by(contact_id=cid).delete()
        db.query(Conversation).filter_by(contact_id=cid).delete()
        db.delete(contact)
        db.commit()
        print(f"Contacto {cid} ({external_id}) borrado con todo su historial.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.reset_contact <external_id> [channel]")
        sys.exit(1)
    reset_contact(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "messenger")