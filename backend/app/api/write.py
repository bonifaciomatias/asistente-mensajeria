from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.xdotool_writer import write_to_active_window


router = APIRouter()


class WriteRequest(BaseModel):
    text: str
    draft_id: int | None = None
    press_enter: bool = True


class WriteResponse(BaseModel):
    ok: bool
    error: str | None = None


def _check_token(authorization: str | None) -> None:
    expected = f"Bearer {settings.api_token}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="invalid_token")


@router.post("/write", response_model=WriteResponse)
def write_endpoint(
    body: WriteRequest,
    authorization: str | None = Header(default=None),
):
    _check_token(authorization)
    ok, err = write_to_active_window(body.text, press_enter=body.press_enter)
    return WriteResponse(ok=ok, error=err)
