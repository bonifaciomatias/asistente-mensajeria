from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.services.ingest import ingest_incoming
from app.services.policy_engine import evaluate, log_decision
from app.services.draft_generator import generate_draft


router = APIRouter()


class IngestEvent(BaseModel):
    channel: str
    external_id: str
    display_name: str
    body: str
    raw_payload: dict | None = None


class DraftPayload(BaseModel):
    id: int
    body: str
    status: str


class IngestResponse(BaseModel):
    message_id: int
    decision: str
    rule_applied: str
    draft: DraftPayload | None = None


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

    draft_payload = None
    if decision.decision in ("auto_send", "escalate"):
        try:
            draft = generate_draft(db, msg)
            if draft:
                draft_payload = DraftPayload(
                    id=draft.id,
                    body=draft.body,
                    status=draft.draft_status,
                )
        except Exception as exc:
            print(f"[ingest] draft error: {exc}")

    return IngestResponse(
        message_id=msg.id,
        decision=decision.decision,
        rule_applied=decision.rule_applied,
        draft=draft_payload,
    )
