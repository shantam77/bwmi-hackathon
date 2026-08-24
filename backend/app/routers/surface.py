"""GET /api/surface -- the readable API-surface page's data source. Reuses
the MCP server's own tool catalogue rather than maintaining a second,
possibly-drifting copy of the same endpoint list."""

from fastapi import APIRouter

from app.mcp_server import TOOL_CATALOGUE

router = APIRouter()

IMPLEMENTED_ENDPOINTS = [
    {"method": "GET", "path": "/api/health", "purpose": "Liveness check; also issues the session cookie."},
    {"method": "POST", "path": "/api/chat", "purpose": "Conversational turn -- SSE stream of token/tool_call/component/alert/done."},
    {"method": "GET", "path": "/api/session", "purpose": "Rehydration -- full thread, journey status, and active deadlines."},
    {"method": "POST", "path": "/api/clock", "purpose": "Demo Controls -- advances this session's simulated clock, streams any newly fired alerts or the Flow H DecisionBlock."},
    {"method": "POST", "path": "/mcp", "purpose": "Stateless MCP server (2026-07-28 spec) exposing a subset of the domain layer as tools."},
]

PERSISTENCE_BOUNDARY_NOTE = (
    "Journey state is a `journeys`/`pnrs` table keyed by PNR and session_id. In "
    "production the alert engine would read from it on a scheduled tick rather than "
    "on request, so alerts fire whether or not the user has the app open. The domain "
    "layer is pure and takes state as an argument, so that change touches no "
    "business logic."
)


@router.get("/api/surface")
async def api_surface() -> dict:
    return {
        "implemented_endpoints": IMPLEMENTED_ENDPOINTS,
        "proposed_mcp_tools": TOOL_CATALOGUE,
        "persistence_boundary_note": PERSISTENCE_BOUNDARY_NOTE,
    }
