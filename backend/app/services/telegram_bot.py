import time
import httpx
from app.core.config import settings
from app.core.db import SessionLocal
from app.services.ingest import ingest_incoming
from app.services.policy_engine import evaluate, log_decision
from app.services.draft_generator import generate_draft

from datetime import datetime
from app.services.policy_engine import evaluate, log_decision, increment_rate
from app.services.telegram_sender import send_text
from app.models.contact import Contact



def _display_name(user: dict) -> str:
    parts = [user.get("first_name") or "", user.get("last_name") or ""]
    return " ".join(p for p in parts if p).strip() or user.get("username") or str(user.get("id"))


def run_bot() -> None:
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN vacío en .env")

    api = f"https://api.telegram.org/bot{token}"
    offset = 0
    print("[bot] polling iniciado")

    while True:
        try:
            r = httpx.get(
                f"{api}/getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=35,
            )
            r.raise_for_status()
            updates = r.json().get("result", [])
        except KeyboardInterrupt:
            print("[bot] detenido")
            break
        except Exception as exc:
            print(f"[bot] error de red: {exc}. Reintento en 5s")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message")
            if not msg:
                continue
            body = msg.get("text") or "[no-text]"
            user = msg["from"]

            try:
                with SessionLocal() as db:
                    m = ingest_incoming(
                        db,
                        channel="telegram",
                        external_id=str(user["id"]),
                        display_name=_display_name(user),
                        body=body,
                        raw_payload=update,
                    )
                    decision = evaluate(db, m)
                    log_decision(db, m, decision)
                    print(
                        f"[IN] contact={m.contact_id} msg={m.id} "
                        f"-> {decision.decision} ({decision.rule_applied}): {body[:60]}"
                    )

                    if decision.decision in ("auto_send", "escalate"):
                        try:
                            draft = generate_draft(db, m)
                            if draft:
                                print(
                                    f"[DRAFT] msg={draft.id} "
                                    f"status={draft.draft_status} "
                                    f"tok_in={draft.tokens_in} tok_out={draft.tokens_out}: "
                                    f"{draft.body[:80]}"
                                )

                                if decision.decision == "auto_send" and draft.draft_status == "generated":
                                    contact = db.get(Contact, m.contact_id)
                                    if settings.send_mode == "bot_api":
                                        ok, err = send_text(contact.external_id, draft.body)
                                    elif settings.send_mode == "xdotool":
                                        from app.services.xdotool_writer import write_to_active_window
                                        ok, err = write_to_active_window(draft.body, press_enter=True)
                                    else:
                                        ok, err = False, f"unknown_send_mode:{settings.send_mode}"
                                        draft.send_status = "failed"
                                        draft.policy_reason = f"send_failed:{err}"
                                        db.commit()
                                        print(f"[SEND FAIL] msg={draft.id}: {err}")
                        except Exception as exc:
                            print(f"[draft/send] error: {exc}")
            except Exception as exc:
                print(f"[bot] error de ingesta/política: {exc}")


if __name__ == "__main__":
    run_bot()