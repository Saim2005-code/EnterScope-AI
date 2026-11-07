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


def test_ingest_text_document_success(client: TestClient):
    """Test 6: Ingests a new document via /ingest and verifies retrieval under that role."""
    file_content = (
        b"Finance Policy Section 1.1: Q4 Enterprise Budget and Cloud Spend.\n"
        b"The annual cloud infrastructure budget is strictly capped at $1.2M annually.\n"
        b"All discretionary software purchases over $10,000 require CFO signoff."
    )
    files = {
        "file": ("fin_cloud_budget.txt", file_content, "text/plain"),
    }
    data = {
        "department": "finance",
    }
    response = client.post("/ingest", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["file_name"] == "fin_cloud_budget.txt"
    assert res_data["department"] == "finance"
    assert res_data["chunks_count"] >= 1

    # Now verify querying with finance role can retrieve this ingested document
    ask_payload = {
        "query": "What is the annual cloud infrastructure budget cap?",
        "user_role": "finance",
        "top_k": 2,
    }
    ask_response = client.post("/ask", json=ask_payload)
    assert ask_response.status_code == 200
    ask_data = ask_response.json()
    assert ask_data["status"] == "success"
    assert len(ask_data["citations"]) > 0
    assert any(c["source_file"] == "fin_cloud_budget.txt" for c in ask_data["citations"])


def test_ingest_unsupported_file_type(client: TestClient):
    """Test 7: Uploading unsupported file format is rejected with HTTP 400."""
    files = {
        "file": ("malicious_payload.exe", b"MZbinarycontent", "application/octet-stream"),
    }
    data = {
        "department": "engineering",
    }
    response = client.post("/ingest", files=files, data=data)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_ingest_empty_file_rejected(client: TestClient):
    """Test 8: Uploading an empty file is rejected with HTTP 400."""
    files = {
        "file": ("empty_policy.txt", b"", "text/plain"),
    }
    data = {
        "department": "engineering",
    }
    response = client.post("/ingest", files=files, data=data)
    assert response.status_code == 400
    assert "Uploaded file is empty" in response.json()["detail"]
