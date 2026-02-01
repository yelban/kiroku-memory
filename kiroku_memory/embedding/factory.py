"""Embedding provider factory"""

from __future__ import annotations

from typing import Optional

from .base import EmbeddingProvider


# Singleton cache for providers
_provider_cache: dict[str, EmbeddingProvider] = {}


def get_embedding_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    dimensions: Optional[int] = None,
    use_cache: bool = True,
) -> EmbeddingProvider:
    """
    Get an embedding provider based on configuration.

    Args:
        provider: Provider name ('openai' or 'local'). If None, uses config.
        model: Model name override. If None, uses config.
        dimensions: Dimensions override. If None, uses config.
        use_cache: Whether to return cached provider instance.

    Returns:
        EmbeddingProvider instance
    """
    from ..db.config import settings

    # Use config values if not specified
    provider = provider or settings.embedding_provider
    model = model or settings.embedding_model
    dimensions = dimensions or settings.embedding_dimensions

    # Cache key
    cache_key = f"{provider}:{model}:{dimensions}"

    if use_cache and cache_key in _provider_cache:
        return _provider_cache[cache_key]

    # Create provider
    if provider == "local":
        from .local_provider import LocalEmbeddingProvider
        instance = LocalEmbeddingProvider(model_name=model)
    else:
        # Default to OpenAI
        from .openai_provider import OpenAIEmbeddingProvider
        instance = OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model_name=model,
            dimensions=dimensions,
        )

    if use_cache:
        _provider_cache[cache_key] = instance

    return instance


def clear_provider_cache() -> None:
    """Clear the provider cache (useful for testing)"""
    _provider_cache.clear()


async def generate_embedding(
    text: str,
    provider: Optional[str] = None,
    adapt_to_dim: Optional[int] = None,
) -> list[float]:
    """
    Convenience function to generate an embedding.

    Args:
        text: Text to embed
        provider: Provider name override
        adapt_to_dim: If set, adapt vector to this dimension

    Returns:
        Embedding vector
    """
    from ..db.config import settings

    embedding_provider = get_embedding_provider(provider)
    result = await embedding_provider.embed_text(text)

    if adapt_to_dim:
        return embedding_provider.adapt_vector(result.vector, adapt_to_dim)

    # Default adaptation to configured storage dimension
    storage_dim = settings.embedding_dimensions
    if len(result.vector) != storage_dim:
        return embedding_provider.adapt_vector(result.vector, storage_dim)

    return result.vector
