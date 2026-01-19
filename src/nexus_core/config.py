"""Application configuration from environment variables."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://nexus:nexus@localhost:5432/nexus_core"

    # Transfer Station
    transfer_station_path: str = "/transfer_station"

    # Ingestion
    ingestion_worker_poll_interval: int = 60

    # JWT Security
    jwt_public_key: Optional[str] = None
    jwt_private_key: Optional[str] = None
    jwt_issuer: str = "nexus-core-api"
    jwt_algorithm: str = "RS256"

    # Extraction Tools
    docling_version: str = "docling/1.0.0"
    unstructured_version: str = "unstructured/0.10.0"

    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4"

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536  # text-embedding-3-small output dimensions

    # Query & Retrieval
    retrieval_top_k: int = 10
    retrieval_keyword_threshold: int = 10  # tokens for keyword vs vector
    retrieval_hybrid_alpha: float = 0.5    # keyword weight in hybrid mode

    # Feedback
    feedback_score_weight: float = 0.02
    feedback_negative_threshold: int = 10

    # Logging
    log_level: str = "INFO"

    @property
    def sync_database_url(self) -> str:
        """Return synchronous database URL for Alembic."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
