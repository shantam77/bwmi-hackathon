from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_issues_a_session_cookie_on_first_contact():
    client = TestClient(app)
    response = client.get("/api/health")
    assert "session_id" in response.cookies
    assert response.json()["session_id"] == response.cookies["session_id"]


def test_session_id_is_stable_across_requests_with_the_same_cookie():
    client = TestClient(app)
    first = client.get("/api/health")
    session_id = first.json()["session_id"]

    second = client.get("/api/health")
    assert second.json()["session_id"] == session_id


def test_two_clients_without_shared_cookies_get_different_sessions():
    client_a = TestClient(app)
    client_b = TestClient(app)

    session_a = client_a.get("/api/health").json()["session_id"]
    session_b = client_b.get("/api/health").json()["session_id"]

    assert session_a != session_b


def test_health_does_not_error_when_credentials_are_stripped():
    # Edge case from the Phase 0 test gate: a request with no cookie jar at
    # all (credentials omitted) must still succeed -- it just starts a new
    # session rather than failing the request.
    client = TestClient(app)
    assert len(client.cookies) == 0
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["session_id"]
