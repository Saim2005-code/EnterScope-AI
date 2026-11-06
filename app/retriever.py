import logging
import time
from typing import Any

from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from groq import Groq
from qdrant_client import QdrantClient, models

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict Enterprise Audit & Knowledge Assistant.
Answer the user's question ONLY using the verified context chunks provided below.

CRITICAL RULES:
1. Every factual claim MUST include an inline citation in the exact format:
   [filename.pdf, Page X].
2. Do NOT extrapolate, guess, or use outside knowledge.
3. If the provided context does not explicitly contain the answer, respond ONLY with:
   "Insufficient permissions or data not found for your role."
"""


class EnterpriseRAGRetriever:
    def __init__(self) -> None:
        logger.info("Initializing Qdrant client and ONNX models...")
        self.qdrant = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.embedder = TextEmbedding(
            model_name=settings.EMBEDDING_MODEL,
            cache_dir=str(settings.FASTEMBED_CACHE_DIR),
        )
        self.reranker = TextCrossEncoder(
            model_name=settings.RERANKER_MODEL,
            cache_dir=str(settings.FASTEMBED_CACHE_DIR),
        )
        self.groq_client = (
            Groq(api_key=settings.GROQ_API_KEY)
            if settings.GROQ_API_KEY
            and settings.GROQ_API_KEY
            not in ("your_groq_api_key_here", "your_groq_api_here")
            else None
        )

    def answer_query(
        self,
        query: str,
        user_role: str,
        top_k: int = 3,
        score_threshold: float = -3.0,
    ) -> dict[str, Any]:
        """
        Executes Pipeline 3 (RBAC Retrieval + Rerank) & Pipeline 4 (Guardrailed LLM).
        """
        total_start = time.perf_counter()
        retrieval_start = time.perf_counter()

        normalized_role = user_role.strip().lower()
        filter_str = f"department == '{normalized_role}'"

        # 1. Embed the user query via ONNX
        query_vector = next(iter(self.embedder.embed([query]))).tolist()

        # 2. Enforce Strict Qdrant RBAC Payload Filter
        rbac_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="department",
                    match=models.MatchValue(value=normalized_role),
                )
            ]
        )

        search_result = self.qdrant.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=query_vector,
            query_filter=rbac_filter,
            limit=10,
            with_payload=True,
        ).points

        # Short-circuit if no documents exist for this role
        if not search_result:
            retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
            return self._abstain_response(normalized_role, filter_str, retrieval_ms)

        # 3. Two-Stage ONNX Cross-Encoder Reranking
        candidate_texts = [(pt.payload or {}).get("text", "") for pt in search_result]
        rerank_scores = list(self.reranker.rerank(query, candidate_texts))

        scored_candidates = sorted(
            zip(search_result, rerank_scores, strict=True),
            key=lambda x: x[1],
            reverse=True,
        )

        verified_hits = [
            (pt, float(score))
            for pt, score in scored_candidates[:top_k]
            if float(score) >= score_threshold
        ]

        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        if not verified_hits:
            return self._abstain_response(normalized_role, filter_str, retrieval_ms)

        # 4. Build Citations & Context Block for LLM
        citations: list[dict[str, Any]] = []
        context_blocks: list[str] = []

        for pt, score in verified_hits:
            payload = pt.payload or {}
            source_file = payload.get("source_file", "unknown")
            page_number = payload.get("page_number", 0)
            department = payload.get("department", normalized_role)
            text_content = payload.get("text", "")

            citations.append(
                {
                    "source_file": source_file,
                    "page_number": page_number,
                    "department": department,
                    "rerank_score": round(score, 4),
                    "chunk_preview": text_content[:160] + "...",
                }
            )
            context_blocks.append(
                f"SOURCE: [{source_file}, Page {page_number}]\nCONTENT: {text_content}"
            )

        # 5. Guardrailed LLM Generation
        llm_start = time.perf_counter()
        answer_text = self._generate_llm_answer(
            query, "\n\n---\n\n".join(context_blocks)
        )
        llm_ms = (time.perf_counter() - llm_start) * 1000
        total_ms = (time.perf_counter() - total_start) * 1000

        return {
            "status": "success",
            "answer": answer_text,
            "citations": citations,
            "telemetry": {
                "Access_Filter_Applied": filter_str,
                "retrieval_and_rerank_ms": round(retrieval_ms, 2),
                "llm_generation_ms": round(llm_ms, 2),
                "total_latency_ms": round(total_ms, 2),
            },
        }

    def _generate_llm_answer(self, query: str, formatted_context: str) -> str:
        if not self.groq_client:
            return (
                f"[DRY-RUN MODE: Set GROQ_API_KEY in .env for live "
                f"{settings.LLM_MODEL} synthesis]\n"
                f"Verified Context Retrieved:\n{formatted_context}"
            )

        completion = self.groq_client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"VERIFIED CONTEXT:\n{formatted_context}\n\n"
                        f"USER QUESTION: {query}"
                    ),
                },
            ],
        )
        return completion.choices[0].message.content.strip()

    @staticmethod
    def _abstain_response(
        role: str, filter_str: str, retrieval_ms: float
    ) -> dict[str, Any]:
        return {
            "status": "abstained",
            "answer": (
                "Insufficient permissions or data not found. No verified "
                f"documents matching your role ('{role}') contain relevant "
                "information for this query."
            ),
            "citations": [],
            "telemetry": {
                "Access_Filter_Applied": filter_str,
                "retrieval_and_rerank_ms": round(retrieval_ms, 2),
                "llm_generation_ms": 0.0,
                "total_latency_ms": round(retrieval_ms, 2),
            },
        }
