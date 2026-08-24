"""Stateless Streamable HTTP MCP server targeting the 2026-07-28 spec
(docs/04-implementation-plan.md section 4.5). Thin wrapper over app/domain
-- duplicates nothing.

Implementation note on "targeting the spec": that revision is dated after
this codebase's knowledge cutoff and after real-world "now" -- it's a
fictional future spec for this project. There is no real `mcp` Python
package to import against it, and a live web fetch would only find the
actual (older, stateful) MCP spec, not this one. The implementation plan's
own section 4.5 is the most authoritative description of the target
protocol available here, so this hand-implements a plain JSON-RPC 2.0
Streamable HTTP endpoint directly against ITS documented requirements,
rather than depend on a package that can't plausibly support a spec dated
past this build's own knowledge horizon.

What the spec (per the plan) requires:
- No initialize handshake, no Mcp-Session-Id header, no protocol-level
  session. Every request stands alone.
- Every stateful tool call takes session_id as an explicit ordinary
  argument (SEP-2567) -- our session_id is exactly that "server-minted
  handle."
- Every POST needs an Mcp-Method header; calls that target something
  (tools/call) also need Mcp-Name; every request needs
  MCP-Protocol-Version, which must match `_meta.protocolVersion` in the
  body. A mismatch is rejected with HTTP 400 and JSON-RPC error -32020
  (HeaderMismatch).
- tools/list returns a deterministic order with ttlMs and cacheScope set.
- Safe behind a round-robin load balancer with no sticky sessions -- true
  by construction here, since every handler goes through app/store, never
  in-memory state.

Exposes a representative subset of app/domain as tools (search, waitlist,
PNR lookup, TDR eligibility) -- proving the pattern, not mirroring every
chat tool one-to-one. See open_issues.md."""

from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app import store
from app.domain import search as search_domain
from app.domain import stations as stations_domain
from app.domain import tdr as tdr_domain
from app.domain import waitlist as waitlist_domain
from app.engine import state as state_engine

router = APIRouter()

PROTOCOL_VERSION = "2026-07-28"
TOOLS_LIST_TTL_MS = 3_600_000  # 1 hour -- this catalogue doesn't change at runtime
CACHE_SCOPE = "global"


def _rpc_error(request_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _rpc_result(request_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


TOOL_CATALOGUE = [
    {
        "name": "search_trains",
        "description": "Direct or single-interchange connecting routes between two station codes, with waitlist predictions attached.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "from_code": {"type": "string"},
                "to_code": {"type": "string"},
                "date": {"type": "string"},
                "travel_class": {"type": "string"},
            },
            "required": ["session_id", "from_code", "to_code", "date"],
        },
    },
    {
        "name": "resolve_station",
        "description": "Resolve a station name/code/alias to one or more station codes, flagging ambiguity.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}, "query": {"type": "string"}},
            "required": ["session_id", "query"],
        },
    },
    {
        "name": "get_confirmation_probability",
        "description": "Waitlist confirmation band and probability for a given status/quota/position.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "status": {"type": "string"},
                "quota": {"type": "string"},
                "position": {"type": "integer"},
            },
            "required": ["session_id", "status", "quota", "position"],
        },
    },
    {
        "name": "get_pnr_status",
        "description": "Look up a previously booked PNR's status for the given session.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}, "pnr": {"type": "string"}},
            "required": ["session_id", "pnr"],
        },
    },
    {
        "name": "check_tdr_eligibility",
        "description": "TDR eligibility, reason code, deadline and auto-refund status for a booked PNR.",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}, "pnr": {"type": "string"}},
            "required": ["session_id", "pnr"],
        },
    },
]


def _tool_search_trains(args: dict) -> dict:
    plans = search_domain.search(
        args["from_code"], args["to_code"], args["date"], args.get("travel_class")
    )
    return {"options": [p.model_dump() for p in plans]}


def _tool_resolve_station(args: dict) -> dict:
    resolution = stations_domain.resolve(args["query"])
    return resolution.model_dump()


def _tool_get_confirmation_probability(args: dict) -> dict:
    prediction = waitlist_domain.predict(args["status"], args["quota"], args["position"])
    return prediction.model_dump()


def _tool_get_pnr_status(args: dict) -> dict:
    record = store.get_pnr(args["session_id"], args["pnr"])
    if record is None:
        raise LookupError(f"No booking found for PNR {args['pnr']}.")
    return record.model_dump()


def _tool_check_tdr_eligibility(args: dict) -> dict:
    record = store.get_pnr(args["session_id"], args["pnr"])
    if record is None:
        raise LookupError(f"No booking found for PNR {args['pnr']}.")
    status = state_engine.compute_status(args["session_id"], record)
    if status.is_cancelled:
        eligibility = tdr_domain.check_cancellation_eligibility()
    elif status.tdr_auto_refund:
        eligibility = tdr_domain.check_waitlist_not_cleared_eligibility()
    else:
        from datetime import timedelta

        eligibility = tdr_domain.check_delay_eligibility(
            timedelta(minutes=status.delay_minutes), state_engine.scheduled_departure(record)
        )
    return {"delay_minutes": status.delay_minutes, **eligibility.model_dump()}


TOOL_HANDLERS = {
    "search_trains": _tool_search_trains,
    "resolve_station": _tool_resolve_station,
    "get_confirmation_probability": _tool_get_confirmation_probability,
    "get_pnr_status": _tool_get_pnr_status,
    "check_tdr_eligibility": _tool_check_tdr_eligibility,
}


@router.post("/mcp")
async def mcp_endpoint(
    request: Request,
    mcp_method: str | None = Header(default=None, alias="Mcp-Method"),
    mcp_name: str | None = Header(default=None, alias="Mcp-Name"),
    mcp_protocol_version: str | None = Header(default=None, alias="MCP-Protocol-Version"),
) -> JSONResponse:
    body = await request.json()
    request_id = body.get("id")
    method = body.get("method")
    meta = body.get("_meta", {})
    body_protocol_version = meta.get("protocolVersion")

    # Header/body agreement is mandatory -- reject a mismatch outright.
    if mcp_method is not None and mcp_method != method:
        return JSONResponse(
            status_code=400,
            content=_rpc_error(request_id, -32020, "HeaderMismatch: Mcp-Method disagrees with body method"),
        )
    if mcp_protocol_version is not None and body_protocol_version is not None:
        if mcp_protocol_version != body_protocol_version:
            return JSONResponse(
                status_code=400,
                content=_rpc_error(
                    request_id, -32020, "HeaderMismatch: MCP-Protocol-Version disagrees with _meta.protocolVersion"
                ),
            )

    if method == "tools/list":
        return JSONResponse(
            content=_rpc_result(
                request_id,
                {"tools": TOOL_CATALOGUE, "ttlMs": TOOLS_LIST_TTL_MS, "cacheScope": CACHE_SCOPE},
            )
        )

    if method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        if mcp_name is not None and mcp_name != name:
            return JSONResponse(
                status_code=400,
                content=_rpc_error(request_id, -32020, "HeaderMismatch: Mcp-Name disagrees with params.name"),
            )
        arguments = params.get("arguments", {})
        if "session_id" not in arguments:
            return JSONResponse(
                status_code=400,
                content=_rpc_error(request_id, -32602, "session_id is required on every tool call"),
            )
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return JSONResponse(
                status_code=404, content=_rpc_error(request_id, -32601, f"Unknown tool: {name}")
            )
        try:
            result = handler(arguments)
        except LookupError as e:
            return JSONResponse(content=_rpc_result(request_id, {"error": str(e)}))
        except (KeyError, ValueError) as e:
            return JSONResponse(
                status_code=400, content=_rpc_error(request_id, -32602, f"Invalid arguments: {e}")
            )
        return JSONResponse(content=_rpc_result(request_id, result))

    return JSONResponse(
        status_code=404, content=_rpc_error(request_id, -32601, f"Unknown method: {method}")
    )
