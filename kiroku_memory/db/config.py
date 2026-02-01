"""Configuration settings for memory system"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Database backend (postgres or surrealdb)
    backend: str = "postgres"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/memory"

    # SurrealDB settings (for future use)
    surreal_url: str = "file://./data/kiroku"
    surreal_namespace: str = "kiroku"
    surreal_database: str = "memory"

    # Embeddings
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_provider: str = "openai"  # openai or local

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
