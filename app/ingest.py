import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF
from fastembed import TextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# Fixed namespace for deterministic UUIDv5 generation (prevents duplicate chunks on re-runs)
UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def infer_department_from_filename(filename: str) -> str:
    """Maps file prefixes to strict RBAC department roles."""
    prefix = filename.lower().split("_")[0]
    role_map = {
        "eng": "engineering",
        "hr": "hr",
        "fin": "finance",
    }
    return role_map.get(prefix, "general")


def extract_and_chunk_pdfs(data_dir: Path) -> List[Dict[str, Any]]:
    """Pipeline 1: Extracts text page-by-page from PDFs and splits into tagged chunks."""
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in {data_dir}. Run 'python scripts/generate_sample_pdfs.py' first."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    structured_chunks: List[Dict[str, Any]] = []

    for pdf_path in pdf_files:
        department = infer_department_from_filename(pdf_path.name)
        doc = fitz.open(pdf_path)

        for page_index in range(len(doc)):
            page_number = page_index + 1
            raw_text = doc[page_index].get_text("text").strip()
            if not raw_text:
                continue

            chunks = splitter.split_text(raw_text)
            for chunk_idx, chunk_text in enumerate(chunks):
                # Deterministic ID: same file + page + chunk index always yields the same UUID
                unique_key = f"{pdf_path.name}::page_{page_number}::chunk_{chunk_idx}"
                point_id = str(uuid.uuid5(UUID_NAMESPACE, unique_key))

                structured_chunks.append(
                    {
                        "id": point_id,
                        "text": chunk_text,
                        "payload": {
                            "text": chunk_text,
                            "source_file": pdf_path.name,
                            "page_number": page_number,
                            "chunk_index": chunk_idx,
                            "department": department,
                        },
                    }
                )
        doc.close()
        logger.info(
            f"Parsed '{pdf_path.name}' -> Assigned RBAC Role: [department={department}]"
        )

    return structured_chunks


def init_qdrant_collection(client: QdrantClient) -> None:
    """Creates the Qdrant collection and configures a Multi-Tenant Payload Index."""
    existing = [c.name for c in client.get_collections().collections]

    if settings.COLLECTION_NAME not in existing:
        logger.info(
            f"Creating Qdrant collection '{settings.COLLECTION_NAME}' (dim={settings.EMBEDDING_DIM}, Cosine)..."
        )
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        )
        # Enterprise Optimization: Index 'department' with is_tenant=True for fast RBAC filtering
        client.create_payload_index(
            collection_name=settings.COLLECTION_NAME,
            field_name="department",
            field_schema=models.KeywordIndexParams(
                type=models.KeywordIndexType.KEYWORD,
                is_tenant=True,
            ),
        )
        logger.info("Configured multi-tenant payload index on field: 'department'.")
    else:
        logger.info(
            f"Collection '{settings.COLLECTION_NAME}' already exists. Performing idempotent upsert..."
        )


def run_ingestion() -> None:
    """Pipeline 2: Embeds chunks with quantized ONNX and upserts into Qdrant."""
    start_time = time.perf_counter()

    # 1. Extract & Chunk
    chunks = extract_and_chunk_pdfs(settings.DATA_DIR)
    logger.info(f"Prepared {len(chunks)} total chunks across all PDFs.")

    # 2. Initialize Quantized ONNX Embedding Model
    logger.info(f"Loading ONNX Embedding Model: {settings.EMBEDDING_MODEL}...")
    embedder = TextEmbedding(
        model_name=settings.EMBEDDING_MODEL,
        cache_dir=str(settings.FASTEMBED_CACHE_DIR),
    )

    texts_to_embed = [item["text"] for item in chunks]
    embeddings = list(embedder.embed(texts_to_embed))

    # 3. Connect to Qdrant & Ensure Collection + Tenant Index Exist
    client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    init_qdrant_collection(client)

    # 4. Build PointStructs and Upsert
    points = [
        models.PointStruct(
            id=chunk["id"],
            vector=vector.tolist(),
            payload=chunk["payload"],
        )
        for chunk, vector in zip(chunks, embeddings)
    ]

    client.upsert(
        collection_name=settings.COLLECTION_NAME,
        points=points,
        wait=True,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    collection_info = client.get_collection(settings.COLLECTION_NAME)
    logger.info(
        f"Ingestion complete in {elapsed_ms:.1f} ms! "
        f"Total points stored in Qdrant: {collection_info.points_count}"
    )


if __name__ == "__main__":
    run_ingestion()