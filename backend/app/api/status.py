from datetime import datetime
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.policy_engine import _is_out_of_hours


router = APIRouter()


class StatusResponse(BaseModel):
    in_business_hours: bool
    reason: str
    timezone: str
    hours_start: int
    hours_end: int


def _check_token(authorization: str | None) -> None:
    expected = f"Bearer {settings.api_token}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="invalid_token")


@router.get("/status", response_model=StatusResponse)
def status(authorization: str | None = Header(default=None)):
    _check_token(authorization)
    out = _is_out_of_hours(datetime.utcnow())
    return StatusResponse(
        in_business_hours=not out,
        reason="out_of_hours" if out else "in_hours",
        timezone=settings.business_timezone,
        hours_start=settings.business_hours_start,
        hours_end=settings.business_hours_end,
    )