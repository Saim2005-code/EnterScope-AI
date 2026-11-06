import logging
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.retriever import EnterpriseRAGRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# Global singleton instance initialized once at server startup
rag_engine: EnterpriseRAGRetriever | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads ONNX embedding & reranker models into memory once on startup."""
    global rag_engine
    logger.info("Starting up FastAPI: Loading ONNX models and connecting to Qdrant...")
    rag_engine = EnterpriseRAGRetriever()
    logger.info("EnterpriseRAGRetriever singleton initialized and ready.")
    yield
    logger.info("Shutting down Enterprise RAG API...")
    rag_engine = None


app = FastAPI(
    title="Enterprise Multi-Tenant RAG & Audit Assistant",
    version="1.0.0",
    description=(
        "Production-grade RAG microservice enforcing Qdrant RBAC payload filtering, "
        "ONNX Cross-Encoder reranking, and strict source citations."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Request & Response Contracts
# ==========================================
class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language question for the enterprise knowledge base.",
        examples=[
            ("What is our maximum PostgreSQL failover RTO and how does Patroni promote replicas?")
        ],
    )
    user_role: Literal["engineering", "hr", "finance"] = Field(
        ...,
        description=("Strict RBAC department role used to filter Qdrant vector payloads."),
        examples=["engineering"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description=("Maximum number of verified chunks to pass to the LLM after reranking."),
    )


class Citation(BaseModel):
    source_file: str
    page_number: int
    department: str
    rerank_score: float
    chunk_preview: str


class Telemetry(BaseModel):
    Access_Filter_Applied: str
    retrieval_and_rerank_ms: float
    llm_generation_ms: float
    total_latency_ms: float


class QueryResponse(BaseModel):
    status: Literal["success", "abstained"]
    answer: str
    citations: list[Citation]
    telemetry: Telemetry


# ==========================================
# API Endpoints
# ==========================================
@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    """Redirects root browser visits directly to the interactive Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """Readiness probe verifying both FastAPI and Qdrant collection connectivity."""
    if rag_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG Engine is still initializing.",
        )
    try:
        collections = rag_engine.qdrant.get_collections().collections
        collection_names = [c.name for c in collections]
        return {
            "status": "healthy",
            "service": "enterprise-rag-api",
            "qdrant_connected": True,
            "active_collections": collection_names,
        }
    except Exception as exc:
        logger.error(f"Qdrant health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Qdrant connection failed: {exc!s}",
        ) from exc


@app.post("/ask", response_model=QueryResponse, status_code=status.HTTP_200_OK)
def ask_question(payload: QueryRequest) -> dict[str, Any]:
    """
    Executes synchronous CPU-bound ONNX embedding/reranking and Qdrant search
    inside FastAPI's threadpool so the main asyncio event loop is never blocked.
    """
    if rag_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG Engine is not initialized.",
        )

    try:
        return rag_engine.answer_query(
            query=payload.query,
            user_role=payload.user_role,
            top_k=payload.top_k,
        )
    except Exception as exc:
        logger.exception("Unhandled error during /ask execution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal RAG pipeline error: {exc!s}",
        ) from exc
