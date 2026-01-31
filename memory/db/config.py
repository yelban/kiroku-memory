"""Configuration settings for memory system"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/memory"

    # Embeddings
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
