from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.message import Message
from app.services.policy_engine import increment_rate


router = APIRouter()


class ConfirmBody(BaseModel):
    reason: str | None = None


def _check_token(authorization: str | None) -> None:
    expected = f"Bearer {settings.api_token}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="invalid_token")


@router.post("/drafts/{draft_id}/sent")
def mark_sent(
    draft_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _check_token(authorization)
    draft = db.get(Message, draft_id)
    if not draft or draft.direction != "out":
        raise HTTPException(status_code=404, detail="draft_not_found")
    if draft.send_status == "sent":
        return {"ok": True, "already": True}

    draft.send_status = "sent"
    draft.sent_at = datetime.utcnow()
    db.commit()

    increment_rate(db, "global", "day")
    increment_rate(db, "contact", "day", draft.contact_id)

    return {"ok": True, "draft_id": draft.id}


@router.post("/drafts/{draft_id}/failed")
def mark_failed(
    draft_id: int,
    body: ConfirmBody,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _check_token(authorization)
    draft = db.get(Message, draft_id)
    if not draft or draft.direction != "out":
        raise HTTPException(status_code=404, detail="draft_not_found")

    draft.send_status = "failed"
    draft.policy_reason = f"send_failed:{body.reason or 'unknown'}"
    db.commit()
    return {"ok": True, "draft_id": draft.id}
