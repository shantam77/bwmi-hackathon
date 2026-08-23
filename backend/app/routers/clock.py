"""POST /api/clock -- Demo Controls. Advances THIS session's clock only,
recomputes journey status, evaluates alerts, and streams newly fired alerts
via the same frozen SSE contract as /api/chat (alert/done)."""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import store
from app.agent.runner import sse
from app.engine import alerts, state

router = APIRouter()


class ClockRequest(BaseModel):
    demo_state: str  # one of app.engine.state.DEMO_STATES, or "reset"


async def _clock_stream(session_id: str, demo_state: str) -> AsyncIterator[str]:
    pnr = store.latest_pnr(session_id)
    if pnr is None:
        yield sse("done")
        return

    state.apply_demo_state(session_id, pnr, demo_state)
    status = state.compute_status(session_id, pnr)
    fired = alerts.evaluate(session_id, pnr, status)
    offset_seconds = store.get_clock_offset_seconds(session_id)

    for alert in fired:
        props = {
            "alert_id": alert.alert_id,
            "severity": alert.severity,
            "message": alert.message,
            "action": alert.action,
            # Any deadline_iso in the payload is expressed on the SIMULATED
            # clock's timeline, which can be months from the browser's real
            # wall-clock time (the persona date is in September). The
            # frontend countdown needs this to compute "now" correctly --
            # see CountdownChip.
            "clock_offset_seconds": offset_seconds,
            **alert.payload,
        }
        store.append_message(
            session_id,
            "agent",
            alert.message,
            component={"component": "AlertMessage", "props": props},
        )
        yield sse("alert", severity=alert.severity, props=props)

    yield sse("done")


@router.post("/api/clock")
async def clock_endpoint(request: Request, body: ClockRequest) -> StreamingResponse:
    session_id = request.state.session_id
    return StreamingResponse(
        _clock_stream(session_id, body.demo_state), media_type="text/event-stream"
    )
