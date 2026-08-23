"""GET /api/session -- rehydration. Built now, not retrofitted, per
docs/04-implementation-plan.md section 4.4. The frontend calls this on
mount, before accepting input, and rebuilds the thread from it -- including
any component payload (OptionCard/PaymentSheet/PNRConfirmation) that was on
screen before a refresh."""

from fastapi import APIRouter, Request

from app import store

router = APIRouter()


@router.get("/api/session")
async def get_session(request: Request) -> dict:
    session_id = request.state.session_id
    messages = store.list_messages(session_id)
    offset_seconds = store.get_clock_offset_seconds(session_id)

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
        # Populated once the Phase 3 state machine exists. Present now so the
        # response shape doesn't change out from under the frontend later.
        "journey": None,
        "state": None,
        "active_deadlines": [],
    }
