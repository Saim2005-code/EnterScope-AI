import pytest
from fastapi.testclient import TestClient

from app.ingest import run_ingestion
from app.main import app
from scripts.generate_sample_pdfs import create_pdfs


@pytest.fixture(scope="module")
def client():
    """
    Guarantees sample PDFs are generated and ingested into Qdrant before tests execute,
    then boots the FastAPI app inside a lifespan context so ONNX models load once.
    """
    create_pdfs()
    run_ingestion()
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient):
    """Test 1: Readiness probe returns 200 OK and confirms Qdrant collection is active."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["qdrant_connected"] is True
    assert "enterprise_docs" in data["active_collections"]


def test_authorized_engineering_query(client: TestClient):
    """Test 2: Engineering role retrieves verified engineering architecture chunks."""
    payload = {
        "query": "What is our maximum PostgreSQL failover RTO and how does Patroni promote replicas?",
        "user_role": "engineering",
        "top_k": 2,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert len(data["citations"]) > 0
    assert data["citations"][0]["source_file"] == "eng_system_design.pdf"
    assert data["citations"][0]["department"] == "engineering"
    assert data["telemetry"]["Access_Filter_Applied"] == "department == 'engineering'"


def test_unauthorized_rbac_snooping_blocked(client: TestClient):
    """
    Test 3 (Critical Security Gate): Engineering user asking about HR executive bonuses
    must be blocked by Qdrant RBAC filter and short-circuit with 0.0ms LLM latency.
    """
    payload = {
        "query": "What is the Vice President target cash bonus percentage and severance cap?",
        "user_role": "engineering",
        "top_k": 2,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "abstained"
    assert data["citations"] == []
    assert data["telemetry"]["llm_generation_ms"] == 0.0
    assert data["telemetry"]["Access_Filter_Applied"] == "department == 'engineering'"


def test_authorized_hr_query(client: TestClient):
    """Test 4: HR role querying the exact same executive bonus question succeeds."""
    payload = {
        "query": "What is the Vice President target cash bonus percentage and severance cap?",
        "user_role": "hr",
        "top_k": 2,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert len(data["citations"]) > 0
    assert data["citations"][0]["source_file"] == "hr_executive_comp.pdf"
    assert data["citations"][0]["department"] == "hr"


def test_invalid_role_rejected_by_pydantic(client: TestClient):
    """Test 5: Unrecognized RBAC role is rejected at the API gateway with HTTP 422."""
    payload = {
        "query": "Show me all company secrets",
        "user_role": "unauthorized_hacker_role",
        "top_k": 2,
    }
    response = client.post("/ask", json=payload)
    assert response.status_code == 422
