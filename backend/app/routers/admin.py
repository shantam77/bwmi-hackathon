"""POST /api/admin/reset-db -- wipes every session's data (all PNRs,
messages, alerts, clock offsets) across the whole deployment. This is
deliberately NOT scoped to the caller's own session, unlike everything else
in this app -- session isolation already means a new visitor sees a clean
slate regardless of this, so the only real reason to call it is hygiene
(clearing out accumulated test data) before a wider audience uses the app.

Gated on ADMIN_RESET_TOKEN: if that env var isn't set, the endpoint refuses
outright rather than allowing an unauthenticated wipe. A global reset button
reachable by anyone who finds the URL is a real risk once this is deployed
publicly -- someone could clear another visitor's in-progress session."""

from fastapi import APIRouter, Header, HTTPException

from app import store
from app.config import ADMIN_RESET_TOKEN

router = APIRouter()


@router.post("/api/admin/reset-db")
async def reset_db(x_admin_token: str | None = Header(default=None)) -> dict:
    if not ADMIN_RESET_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_RESET_TOKEN is not set -- this endpoint is disabled until it is.",
        )
    if x_admin_token != ADMIN_RESET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Token header.")

    counts = store.reset_all_data()
    return {"status": "ok", "rows_deleted": counts, "total": sum(counts.values())}
