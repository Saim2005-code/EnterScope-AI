import io
import logging
import time
import uuid
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import pymupdf as fitz
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


def extract_text_from_file_bytes(filename: str, file_bytes: bytes) -> list[tuple[int, str]]:
    """
    Extracts text as a list of (page_number, text) tuples.
    Supports PDF, DOCX, TXT, and Markdown files.
    """
    lower_name = filename.lower()
    pages: list[tuple[int, str]] = []

    if lower_name.endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_index in range(len(doc)):
            page_text = doc[page_index].get_text("text").strip()
            if page_text:
                pages.append((page_index + 1, page_text))
        doc.close()

    elif lower_name.endswith(".docx"):
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            xml_content = docx_zip.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in tree.iterfind(".//w:p", namespace):
                texts = [node.text for node in p.iterfind(".//w:t", namespace) if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            full_text = "\n\n".join(paragraphs).strip()
            if full_text:
                pages.append((1, full_text))

    elif lower_name.endswith((".txt", ".md")):
        try:
            full_text = file_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            full_text = file_bytes.decode("latin-1").strip()
        if full_text:
            pages.append((1, full_text))

    else:
        # Fallback to PyMuPDF generic stream or plain text decode
        try:
            doc = fitz.open(stream=file_bytes)
            for page_index in range(len(doc)):
                page_text = doc[page_index].get_text("text").strip()
                if page_text:
                    pages.append((page_index + 1, page_text))
            doc.close()
        except (fitz.FileDataError, RuntimeError, OSError):
            try:
                full_text = file_bytes.decode("utf-8").strip()
            except UnicodeDecodeError:
                full_text = file_bytes.decode("latin-1").strip()
            if full_text:
                pages.append((1, full_text))

    return pages


def chunk_extracted_pages(
    filename: str,
    pages: list[tuple[int, str]],
    department: str,
) -> list[dict[str, Any]]:
    """Splits extracted page texts into deterministic tagged chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    structured_chunks: list[dict[str, Any]] = []

    for page_number, raw_text in pages:
        chunks = splitter.split_text(raw_text)
        for chunk_idx, chunk_text in enumerate(chunks):
            unique_key = f"{filename}::page_{page_number}::chunk_{chunk_idx}"
            point_id = str(uuid.uuid5(UUID_NAMESPACE, unique_key))
            structured_chunks.append(
                {
                    "id": point_id,
                    "text": chunk_text,
                    "payload": {
                        "text": chunk_text,
                        "source_file": filename,
                        "page_number": page_number,
                        "chunk_index": chunk_idx,
                        "department": department,
                    },
                }
            )
    return structured_chunks


def extract_and_chunk_pdfs(data_dir: Path) -> list[dict[str, Any]]:
    """Pipeline 1: Extracts text page-by-page from PDFs and splits into tagged chunks."""
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in {data_dir}. Run 'python scripts/generate_sample_pdfs.py' first."
        )

    structured_chunks: list[dict[str, Any]] = []

    for pdf_path in pdf_files:
        department = infer_department_from_filename(pdf_path.name)
        pages = extract_text_from_file_bytes(pdf_path.name, pdf_path.read_bytes())
        file_chunks = chunk_extracted_pages(pdf_path.name, pages, department)
        structured_chunks.extend(file_chunks)
        logger.info(f"Parsed '{pdf_path.name}' -> Assigned RBAC Role: [department={department}]")

    return structured_chunks


def ingest_file_bytes(
    filename: str,
    file_bytes: bytes,
    department: str,
    client: QdrantClient | None = None,
    embedder: TextEmbedding | None = None,
) -> dict[str, Any]:
    """
    Ingests a single file's bytes:
    1. Saves file to DATA_DIR.
    2. Extracts & chunks text.
    3. Generates vector embeddings via ONNX.
    4. Upserts PointStructs into Qdrant collection with department RBAC payload.
    """
    start_time = time.perf_counter()
    normalized_department = department.strip().lower()

    # Save to data directory for persistence
    try:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        persisted_file = settings.DATA_DIR / filename
        persisted_file.write_bytes(file_bytes)
        logger.info(f"Saved uploaded document to {persisted_file}")
    except OSError as exc:
        logger.warning(f"Could not persist uploaded file to {settings.DATA_DIR}: {exc}")

    pages = extract_text_from_file_bytes(filename, file_bytes)
    chunks = chunk_extracted_pages(filename, pages, normalized_department)

    if not chunks:
        logger.warning(f"No text could be extracted or chunked from '{filename}'.")
        return {
            "status": "warning",
            "message": f"No extractable text found in '{filename}'.",
            "file_name": filename,
            "department": normalized_department,
            "chunks_count": 0,
            "total_points_in_collection": None,
        }

    qdrant_client = client or QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    init_qdrant_collection(qdrant_client)

    active_embedder = embedder or TextEmbedding(
        model_name=settings.EMBEDDING_MODEL,
        cache_dir=str(settings.FASTEMBED_CACHE_DIR),
    )

    texts_to_embed = [item["text"] for item in chunks]
    embeddings = list(active_embedder.embed(texts_to_embed))

    points = [
        models.PointStruct(
            id=chunk["id"],
            vector=vector.tolist(),
            payload=chunk["payload"],
        )
        for chunk, vector in zip(chunks, embeddings, strict=True)
    ]

    qdrant_client.upsert(
        collection_name=settings.COLLECTION_NAME,
        points=points,
        wait=True,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    collection_info = qdrant_client.get_collection(settings.COLLECTION_NAME)
    logger.info(
        f"Ingestion of '{filename}' complete in {elapsed_ms:.1f} ms! "
        f"Added {len(chunks)} chunks. Total points in Qdrant: {collection_info.points_count}"
    )

    return {
        "status": "success",
        "message": f"Successfully ingested {len(chunks)} chunks from '{filename}'.",
        "file_name": filename,
        "department": normalized_department,
        "chunks_count": len(chunks),
        "total_points_in_collection": collection_info.points_count,
    }


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
        for chunk, vector in zip(chunks, embeddings, strict=True)
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
