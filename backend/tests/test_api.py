"""
API-level tests using FastAPI's TestClient. These verify routing, request
validation, and response shape -- with the underlying research pipeline
mocked so tests are fast and don't require network or a populated KB.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ResearchResponse

client = TestClient(app)


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"


def test_kb_health_endpoint():
    resp = client.get("/api/v1/kb/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "kb_documents_indexed" in body
    assert "embedding_model" in body


def test_research_endpoint_rejects_short_query():
    resp = client.post("/api/v1/research", json={"query": "hi"})
    assert resp.status_code == 422  # pydantic min_length violation


def test_research_endpoint_rejects_both_sources_disabled():
    resp = client.post(
        "/api/v1/research",
        json={"query": "a valid long enough query here", "include_web": False, "include_kb": False},
    )
    assert resp.status_code == 400


def test_research_endpoint_happy_path_with_mocked_pipeline():
    fake_response = ResearchResponse(
        query="design a low noise current source",
        detected_topics=["Current source / current sink design"],
        global_keywords=[],
        results_by_topic=[],
        all_sources=[],
        web_agent_used=True,
        kb_used=True,
        timing_ms={"total_ms": 12.3},
        warnings=[],
    )

    async def fake_pipeline(*args, **kwargs):
        return fake_response

    with patch("app.api.routers.research.run_hybrid_research", side_effect=fake_pipeline):
        resp = client.post(
            "/api/v1/research",
            json={"query": "design a low noise current source for precision applications"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "design a low noise current source"
    assert body["web_agent_used"] is True
