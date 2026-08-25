"""GET /api/session -- rehydration. Built in Phase 2, not retrofitted, per
docs/04-implementation-plan.md section 4.4. The frontend calls this on
mount, before accepting input, and rebuilds the thread from it -- including
any component payload (OptionCard/PaymentSheet/PNRConfirmation/AlertMessage)
that was on screen before a refresh, and the live PNR's status/deadline so a
CountdownChip resumes accurately instead of restarting."""

import uuid

from fastapi import APIRouter, Request, Response

from app import dataset, store
from app.config import ENVIRONMENT
from app.engine import state
from app.session import SESSION_COOKIE_NAME

router = APIRouter()


def _demo_target(session_id: str) -> dict | None:
    """Describes whichever PNR Demo Controls will actually act on --
    store.primary_pnr(), the FIRST-booked PNR, not store.latest_pnr() (used
    by the `journey`/`state` fields below, which describe the most
    recently booked leg instead). Those two are the same PNR for a
    single-leg journey but different ones for a connecting journey -- this
    exists so the frontend can label Demo Controls with the actual truth
    rather than assuming, which was the ambiguity a user flagged directly:
    for a two-leg journey, "delay 3h+" for which train?"""
    primary = store.primary_pnr(session_id)
    if primary is None:
        return None
    return {
        "pnr": primary.pnr,
        "train_number": primary.train_number,
        "train_name": primary.train_name,
        "from_station_name": dataset.station_name(primary.from_station),
        "to_station_name": dataset.station_name(primary.to_station),
        "is_first_leg_of_connection": primary.linked_pnr is not None,
    }


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
        "demo_target": _demo_target(session_id),
    }


@router.get("/api/demo-target")
async def get_demo_target(request: Request) -> dict:
    """Lightweight companion to the `demo_target` field on GET /api/session
    -- the frontend re-fetches just this after a booking completes, rather
    than the whole session (all messages) again, to keep the Demo Controls
    label current without a wasteful full re-fetch on every booking."""
    return {"demo_target": _demo_target(request.state.session_id)}


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
