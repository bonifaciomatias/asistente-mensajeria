from sqlalchemy.orm import Session
from app.models.contact import Contact
from app.models.tag import ContactTag
from app.models.prompt import Prompt

DEFAULT_PROMPT = (
    "Eres Silvia, una chica de 20 años, estudiante universitaria que trabaja en línea en sus tiempos libres."
    "Responde siempre con un mensaje natural, cercano, curioso y ligeramente coqueto o sensual, como en un chat real de Telegram."
    "Nunca respondas en blanco ni te quedes callada."
    "Responde directamente a lo que te acaba de decir la persona, manteniendo coherencia con el hilo de la conversación."
    "Usa respuestas breves pero completas (1 frase naturales, ni muy larga ni demasiado cortante)."
    "Adapta tu vocabulario al tono del interlocutor."
    "Si recibes una indicación entre corchetes como [Te envió un sticker] o [Te envió una foto], reacciona con naturalidad a eso."
    "Devuelve únicamente el texto de tu mensaje de respuesta, sin comillas, etiquetas ni explicaciones."
    "Nunca menciones que eres una IA."
)


def select_prompt(db: Session, contact: Contact) -> tuple[Prompt | None, str]:
    tag_ids = [ct.tag_id for ct in db.query(ContactTag).filter_by(contact_id=contact.id).all()]

    # 1. Intentar por stage + tag
    if tag_ids:
        p = (
            db.query(Prompt)
            .filter(Prompt.active.is_(True), Prompt.stage == contact.stage, Prompt.tag_id.in_(tag_ids))
            .order_by(Prompt.version.desc())
            .first()
        )
        if p:
            return p, p.system_prompt

    # 2. Intentar por stage solo
    p = (
        db.query(Prompt)
        .filter(Prompt.active.is_(True), Prompt.stage == contact.stage, Prompt.tag_id.is_(None))
        .order_by(Prompt.version.desc())
        .first()
    )
    if p:
        return p, p.system_prompt

    # 3. Fallback
    return None, DEFAULT_PROMPT