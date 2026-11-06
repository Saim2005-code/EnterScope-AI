# Enterprise Multi-Tenant RAG & Audit Assistant

[![Enterprise RAG CI/CD Pipeline](https://github.com/Saim2005-code/Enterprise-Level-RAG-Assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Saim2005-code/Enterprise-Level-RAG-Assistant/actions)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-v1.19.2-dc244c.svg)
![ONNX Runtime](https://img.shields.io/badge/ONNX-FastEmbed-purple.svg)
![LLM](https://img.shields.io/badge/LLM-openai%2Fgpt--oss--120b-orange.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

A production-grade, multi-tenant **Retrieval-Augmented Generation (RAG)** microservice engineered with strict **Role-Based Access Control (RBAC)** at the vector database layer, local **ONNX Bi-Encoder + Cross-Encoder Reranking**, deterministic **UUIDv5 idempotent ingestion**, and guardrailed **`openai/gpt-oss-120b`** synthesis via Groq.

---

## System Architecture

```mermaid
flowchart LR
    subgraph ETL["Pipeline 1 & 2: Idempotent ETL & Indexing"]
        PDF["Enterprise PDFs\n(eng_*, hr_*)"] --> PyMuPDF["PyMuPDF Page Parser\n+ Recursive Splitter"]
        PyMuPDF --> UUID["Deterministic UUIDv5\n(file::page::idx::md5)"]
        UUID --> BiEnc1["ONNX Bi-Encoder\n(BAAI/bge-small-en-v1.5)"]
        BiEnc1 --> Qdrant[(Qdrant Vector DB\nPayload Index: department)]
    end

    subgraph Query["Pipeline 3 & 4: RBAC Retrieval, Reranking & Synthesis"]
        Client["Client POST /ask\n{query, user_role}"] --> FastAPI["FastAPI Gateway\n(Pydantic Validation)"]
        FastAPI --> BiEnc2["ONNX Query Embedder"]
        BiEnc2 --> Filter["Qdrant RBAC Filter\ndepartment == user_role"]
        Qdrant --> Filter
        Filter -->|0 Hits: Short-Circuit| Abstain["Abstain Response\n(0.0ms LLM Latency)"]
        Filter -->|Top-10 Candidates| CrossEnc["ONNX Cross-Encoder Reranker\n(ms-marco-MiniLM-L-6-v2)"]
        CrossEnc -->|Top-K Verified Chunks| Groq["Groq openai/gpt-oss-120b\nStrict Inline Citations"]
        Groq --> Response["JSON Response\n{answer, citations, telemetry}"]
    end
