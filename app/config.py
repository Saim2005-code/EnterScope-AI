from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Project Paths (Native Linux Pathing)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    FASTEMBED_CACHE_DIR: Path = BASE_DIR / ".fastembed_cache"

    # Qdrant Vector DB Config
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "enterprise_docs"

    # ONNX Models (FastEmbed)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384
    RERANKER_MODEL: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    # Chunking Hyperparameters
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # LLM Config (Used in Milestone 2)
    GROQ_API_KEY: str = "your_groq_api_key_here"
    LLM_MODEL: str = "openai/gpt-oss-120b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()