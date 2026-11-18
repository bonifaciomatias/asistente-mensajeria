from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.policy import PolicyLog, RateState


@dataclass
class PolicyDecision:
    decision: str       # auto_send | escalate | silence
    rule_applied: str   # nombre corto y estable
    reason: str         # detalle legible para auditoría


def _is_out_of_hours(now_utc: datetime) -> bool:
    tz = ZoneInfo(settings.business_timezone)
    local = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return not (settings.business_hours_start <= local.hour < settings.business_hours_end)


def _rate_count(db: Session, scope: str, window_kind: str, contact_id: int | None = None) -> int:
    q = db.query(RateState).filter_by(scope=scope, window_kind=window_kind)
    if contact_id is not None:
        q = q.filter_by(contact_id=contact_id)
    rs = q.order_by(RateState.window_start.desc()).first()
    if rs is None:
        return 0
    now = datetime.utcnow()
    if window_kind == "day" and rs.window_start.date() != now.date():
        return 0
    if window_kind == "hour" and rs.window_start.replace(minute=0, second=0, microsecond=0) != now.replace(minute=0, second=0, microsecond=0):
        return 0
    return rs.count or 0


def evaluate(db: Session, message: Message) -> PolicyDecision:
    now = datetime.utcnow()
    contact = db.get(Contact, message.contact_id)
    conversation = db.get(Conversation, message.conversation_id)

    # 1. Override humano activo
    if contact.human_override_until and contact.human_override_until > now:
        return PolicyDecision(
            "silence", "contact_override",
            f"override activo hasta {contact.human_override_until.isoformat()}",
        )

    # 2. Conversación cerrada o marcada como spam
    if conversation.status in ("closed", "spam"):
        return PolicyDecision(
            "silence", "conversation_closed_or_spam",
            f"status={conversation.status}",
        )

    # 3. Fuera de horario
    if _is_out_of_hours(now):
        return PolicyDecision("silence", "out_of_hours", "fuera de ventana horaria")

    # 4. Límite diario global
    if _rate_count(db, "global", "day") >= settings.daily_limit_global:
        return PolicyDecision(
            "silence", "global_daily_limit",
            f"count>={settings.daily_limit_global}",
        )

    # 5. Límite diario por contacto
    if _rate_count(db, "contact", "day", contact.id) >= settings.daily_limit_per_contact:
        return PolicyDecision(
            "silence", "per_contact_daily_limit",
            f"count>={settings.daily_limit_per_contact}",
        )

    # 6. Contacto nuevo: nunca auto-responder a desconocidos
    in_count = (
        db.query(func.count(Message.id))
        .filter_by(contact_id=contact.id, direction="in")
        .scalar()
        or 0
    )
    if in_count <= settings.warmup_max_auto_replies:
        return PolicyDecision(
            "escalate", "new_contact",
            f"in_count={in_count} <= {settings.warmup_max_auto_replies}",
        )

    # 7. Por defecto
    return PolicyDecision("auto_send", "default_auto", "sin reglas de bloqueo aplicadas")


def log_decision(db: Session, message: Message, decision: PolicyDecision) -> None:
    message.policy_decision = decision.decision
    message.policy_reason = f"{decision.rule_applied}: {decision.reason}"

    db.add(PolicyLog(
        message_id=message.id,
        conversation_id=message.conversation_id,
        contact_id=message.contact_id,
        decision=decision.decision,
        rule_applied=decision.rule_applied,
        reason=decision.reason,
    ))
    db.commit()

def increment_rate(
    db: Session,
    scope: str,
    window_kind: str,
    contact_id: int | None = None,
) -> None:
    now = datetime.utcnow()
    q = db.query(RateState).filter_by(
        scope=scope, window_kind=window_kind,
        contact_id=contact_id,
    )
    if window_kind == "day":
        q = q.filter(RateState.window_start >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    elif window_kind == "hour":
        q = q.filter(RateState.window_start >= now.replace(minute=0, second=0, microsecond=0))

    rs = q.order_by(RateState.window_start.desc()).first()
    if rs is None:
        rs = RateState(
            scope=scope, contact_id=contact_id,
            window_kind=window_kind,
            window_start=now,
            count=1,
        )
        db.add(rs)
    else:
        rs.count = (rs.count or 0) + 1
    db.commit()