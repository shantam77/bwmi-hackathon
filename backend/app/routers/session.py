"""GET /api/session -- rehydration. Built in Phase 2, not retrofitted, per
docs/04-implementation-plan.md section 4.4. The frontend calls this on
mount, before accepting input, and rebuilds the thread from it -- including
any component payload (OptionCard/PaymentSheet/PNRConfirmation/AlertMessage)
that was on screen before a refresh, and the live PNR's status/deadline so a
CountdownChip resumes accurately instead of restarting."""

import uuid

from fastapi import APIRouter, Request, Response

from app import store
from app.config import ENVIRONMENT
from app.engine import state
from app.session import SESSION_COOKIE_NAME

router = APIRouter()


@router.get("/api/session")
async def get_session(request: Request) -> dict:
    session_id = request.state.session_id
    messages = store.list_messages(session_id)
    offset_seconds = store.get_clock_offset_seconds(session_id)

    pnr = store.latest_pnr(session_id)
    journey_status = None
    active_deadlines = []
    if pnr is not None:
        journey_status = state.compute_status(session_id, pnr)
        if journey_status.tdr_eligible and journey_status.tdr_deadline_iso:
            active_deadlines.append(
                {
                    "kind": "tdr",
                    "pnr": pnr.pnr,
                    "deadline_iso": journey_status.tdr_deadline_iso,
                }
            )

    return {
        "session_id": session_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "component": m.component_json,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "clock_offset_seconds": offset_seconds,
        "journey": pnr.model_dump() if pnr else None,
        "state": journey_status.model_dump() if journey_status else None,
        "active_deadlines": active_deadlines,
    }


@router.post("/api/session/new")
async def new_session(response: Response) -> dict:
    """Starts a fresh session for the "New chat" action -- issues a new
    session_id cookie, overwriting the old one. The old session's rows are
    left in Postgres untouched (harmless, orphaned, still inspectable if
    ever needed) rather than destructively deleted -- matches how "log out
    and start over" works in a real app, not a wipe."""
    session_id = str(uuid.uuid4())
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=ENVIRONMENT == "production",
        samesite="none" if ENVIRONMENT == "production" else "lax",
        max_age=60 * 60 * 24 * 30,
    )
    return {"session_id": session_id}
