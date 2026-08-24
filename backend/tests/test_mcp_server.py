from fastapi.testclient import TestClient

from app.main import app
from app.mcp_server import PROTOCOL_VERSION

client = TestClient(app)


def _rpc(method, params=None, mcp_method=None, mcp_name=None, protocol_version=PROTOCOL_VERSION, body_protocol_version=PROTOCOL_VERSION):
    headers = {}
    if mcp_method is not None:
        headers["Mcp-Method"] = mcp_method
    if mcp_name is not None:
        headers["Mcp-Name"] = mcp_name
    if protocol_version is not None:
        headers["MCP-Protocol-Version"] = protocol_version
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    if body_protocol_version is not None:
        body["_meta"] = {"protocolVersion": body_protocol_version}
    return client.post("/mcp", json=body, headers=headers)


def test_tools_list_returns_deterministic_order_with_ttl_and_cache_scope():
    r1 = _rpc("tools/list", mcp_method="tools/list")
    r2 = _rpc("tools/list", mcp_method="tools/list")
    assert r1.status_code == 200
    assert r2.status_code == 200
    names_1 = [t["name"] for t in r1.json()["result"]["tools"]]
    names_2 = [t["name"] for t in r2.json()["result"]["tools"]]
    assert names_1 == names_2  # same order every time
    assert r1.json()["result"]["ttlMs"] > 0
    assert r1.json()["result"]["cacheScope"]


def test_tools_list_has_no_session_or_handshake_state():
    # No initialize call was ever made -- the very first request must work.
    r = _rpc("tools/list", mcp_method="tools/list")
    assert r.status_code == 200
    assert "Mcp-Session-Id" not in r.headers


def test_tool_call_without_session_id_is_rejected():
    r = _rpc(
        "tools/call",
        params={"name": "search_trains", "arguments": {"from_code": "SBC", "to_code": "NGP", "date": "2026-09-04"}},
        mcp_method="tools/call",
        mcp_name="search_trains",
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == -32602


def test_mcp_method_header_disagreeing_with_body_is_rejected():
    r = _rpc("tools/list", mcp_method="tools/call")  # header says tools/call, body says tools/list
    assert r.status_code == 400
    assert r.json()["error"]["code"] == -32020


def test_protocol_version_header_disagreeing_with_body_meta_is_rejected():
    r = _rpc("tools/list", mcp_method="tools/list", protocol_version="1999-01-01")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == -32020


def test_mcp_name_header_disagreeing_with_params_name_is_rejected():
    r = _rpc(
        "tools/call",
        params={"name": "search_trains", "arguments": {"session_id": "x", "from_code": "SBC", "to_code": "NGP", "date": "2026-09-04"}},
        mcp_method="tools/call",
        mcp_name="get_pnr_status",  # disagrees with params.name
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == -32020


def test_search_trains_tool_call_succeeds_with_valid_session_id():
    r = _rpc(
        "tools/call",
        params={
            "name": "search_trains",
            "arguments": {
                "session_id": "mcp-test-session",
                "from_code": "SBC",
                "to_code": "NGP",
                "date": "2026-09-04",
                "travel_class": "SL",
            },
        },
        mcp_method="tools/call",
        mcp_name="search_trains",
    )
    assert r.status_code == 200
    options = r.json()["result"]["options"]
    assert any(o["legs"][0]["train_number"] == "12295" for o in options)


def test_unknown_tool_returns_method_not_found():
    r = _rpc(
        "tools/call",
        params={"name": "not_a_real_tool", "arguments": {"session_id": "x"}},
        mcp_method="tools/call",
        mcp_name="not_a_real_tool",
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == -32601


def test_unknown_method_returns_method_not_found():
    r = _rpc("resources/read", mcp_method="resources/read")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == -32601
