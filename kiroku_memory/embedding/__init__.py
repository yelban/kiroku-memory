"""Embedding providers for vector generation"""

from .base import EmbeddingProvider, EmbeddingResult
from .factory import get_embedding_provider, generate_embedding, clear_provider_cache
from .openai_provider import OpenAIEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "EmbeddingResult",
    "get_embedding_provider",
    "generate_embedding",
    "clear_provider_cache",
    "OpenAIEmbeddingProvider",
]

# Lazy import for LocalEmbeddingProvider (requires sentence-transformers)
def __getattr__(name: str):
    if name == "LocalEmbeddingProvider":
        from .local_provider import LocalEmbeddingProvider
        return LocalEmbeddingProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
