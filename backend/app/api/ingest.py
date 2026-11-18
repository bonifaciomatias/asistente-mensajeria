from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.services.ingest import ingest_incoming
from app.services.policy_engine import evaluate, log_decision


router = APIRouter()


class IngestEvent(BaseModel):
    channel: str                  # telegram_web | messenger
    external_id: str
    display_name: str
    body: str
    raw_payload: dict | None = None


class IngestResponse(BaseModel):
    message_id: int
    decision: str
    rule_applied: str


def _check_token(authorization: str | None) -> None:
    expected = f"Bearer {settings.api_token}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="invalid_token")


@router.post("/ingest", response_model=IngestResponse)
def ingest(
    event: IngestEvent,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _check_token(authorization)

    msg = ingest_incoming(
        db,
        channel=event.channel,
        external_id=event.external_id,
        display_name=event.display_name,
        body=event.body,
        raw_payload=event.raw_payload or {},
    )
    decision = evaluate(db, msg)
    log_decision(db, msg, decision)

    return IngestResponse(
        message_id=msg.id,
        decision=decision.decision,
        rule_applied=decision.rule_applied,
    )