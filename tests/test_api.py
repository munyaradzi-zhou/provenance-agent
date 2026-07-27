"""Contract tests for the production API: auth, rate limit, errors, readiness."""

import app.api.main as main
import pytest
from app.core.config import get_settings
from fastapi.testclient import TestClient

CANNED = {
    "answer": "Directed by Albert Pyun [Nemesis 2].",
    "route": "vector",
    "grounded": True,
    "citations": ["Nemesis 2"],
    "trace": [
        "redacted input",
        "supervisor: route=vector",
        "synthesis complete",
        "grader: grounded=True",
    ],
}


class FakeGraph:
    def invoke(self, _state, _config=None):  # _config: LangChain RunnableConfig
        return CANNED


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "compiled_graph", FakeGraph())
    s = get_settings()
    monkeypatch.setattr(s, "api_keys", "secret123")  # enable auth
    return TestClient(main.app)


def test_health_is_liveness(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_query_requires_api_key(client):
    r = client.post("/v1/query", json={"question": "who directed X?"})
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == 401
    assert "request_id" in body["error"]


def test_query_happy_path(client):
    r = client.post(
        "/v1/query", json={"question": "who directed X?"}, headers={"X-API-Key": "secret123"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["answer"].startswith("Directed by")
    assert body["route"] == "vector"
    assert body["grounded"] is True
    assert body["citations"] == ["Nemesis 2"]
    assert body["request_id"]  # non-empty
    assert body["latency_ms"] >= 0
    assert r.headers["X-Request-ID"] == body["request_id"]


def test_empty_question_is_422(client):
    r = client.post("/v1/query", json={"question": "   "}, headers={"X-API-Key": "secret123"})
    assert r.status_code == 422


def test_malformed_body_is_422(client):
    r = client.post("/v1/query", json={"not_question": "x"}, headers={"X-API-Key": "secret123"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == 422


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(main, "compiled_graph", FakeGraph())
    s = get_settings()
    monkeypatch.setattr(s, "api_keys", "rlkey")
    monkeypatch.setattr(s, "rate_limit", "3/minute")
    c = TestClient(main.app)
    headers = {"X-API-Key": "rlkey"}
    codes = [
        c.post("/v1/query", json={"question": "q"}, headers=headers).status_code for _ in range(5)
    ]
    assert 200 in codes and 429 in codes  # some allowed, then throttled


def test_ready_reports_dependencies(client):
    r = client.get("/ready")
    assert r.status_code in (200, 503)
    body = r.json()
    assert set(body["dependencies"]) == {"neo4j", "qdrant"}
