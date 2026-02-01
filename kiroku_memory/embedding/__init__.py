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
    # Backward compatibility
    "embed_item",
    "search_similar",
    "batch_embed_items",
]


# Backward compatibility: import from old embedding.py location
# These functions use SQLAlchemy sessions directly (PostgreSQL only)
def __getattr__(name: str):
    if name == "LocalEmbeddingProvider":
        from .local_provider import LocalEmbeddingProvider
        return LocalEmbeddingProvider

    # Backward compatibility imports
    if name in ("embed_item", "search_similar", "batch_embed_items"):
        # Import from the standalone embedding module (renamed)
        import importlib.util
        from pathlib import Path

        # Load the old embedding.py as a separate module
        old_module_path = Path(__file__).parent.parent / "embedding_legacy.py"
        if not old_module_path.exists():
            # Fallback: the old functions might have been moved
            raise AttributeError(
                f"Legacy function {name!r} not found. "
                "Use the new provider-based API instead."
            )

        spec = importlib.util.spec_from_file_location("embedding_legacy", old_module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
