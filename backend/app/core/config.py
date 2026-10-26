import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    # pyrefly: ignore[unexpected-keyword]
    model_config = ConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")

    PROJECT_NAME: str = "AI Insurance Assistant - PDF Ingestion Pipeline"
    API_PREFIX: str = "/api"
    
    # Base directory paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    SOURCE_PDFS_DIR: Path = DATA_DIR / "source_pdfs"
    STAGING_DIR: Path = DATA_DIR / "staging"
    REPORTS_DIR: Path = DATA_DIR / "reports"
    CHROMA_DB_DIR: Path = DATA_DIR / "chroma_db"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Parent document store & history
    PARENT_STORE_PATH: Path = STAGING_DIR / "parent_store.json"
    HISTORY_STORE_PATH: Path = STAGING_DIR / "ingestion_history.json"
    
    # ChromaDB Configuration (Cloud & Remote Credentials)
    CHROMA_MODE: str = "cloud"  # 'cloud', 'remote', or 'local'
    CHROMA_COLLECTION_NAME: str = "insurance_knowledge"
    
    # Chroma Cloud Settings (https://cloud.trychroma.com)
    CHROMA_API_KEY: str = ""
    CHROMA_TENANT: str = "643b668b-9e6d-4739-ab36-2fcab1d7ad2a"
    CHROMA_DATABASE: str = "tibil_intern"
    CHROMA_CLOUD_HOST: str = "api.trychroma.com"
    CHROMA_CLOUD_PORT: int = 443
    
    # Remote Self-Hosted Chroma HTTP Settings (Optional alternative)
    CHROMA_SERVER_HOST: str = ""
    CHROMA_SERVER_PORT: int = 8000
    CHROMA_SERVER_SSL: bool = True
    CHROMA_SERVER_AUTH_TOKEN: str = ""
    
    # Embedding Configuration
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32
    
    # Chunking Configuration
    TARGET_CHUNK_TOKENS_MIN: int = 450
    TARGET_CHUNK_TOKENS_MAX: int = 550
    CHUNK_OVERLAP_TOKENS: int = 80
    
    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_FALLBACK_MODEL: str = "gemini-flash-latest"

    # Upload limits & security
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS: set[str] = {".pdf"}
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    MAX_QUERY_CHARS: int = 2000
    MAX_CONTEXT_TOKENS: int = 4000
    MAX_HISTORY_TURNS: int = 5

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.SOURCE_PDFS_DIR.mkdir(parents=True, exist_ok=True)
settings.STAGING_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
