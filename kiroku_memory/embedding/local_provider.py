"""Local embedding provider using sentence-transformers"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Optional

from .base import EmbeddingProvider, EmbeddingResult


# Lazy import to avoid loading torch if not needed
_model_cache: dict[str, "SentenceTransformer"] = {}


def _get_model(model_name: str) -> "SentenceTransformer":
    """Get or load a sentence-transformers model (cached)"""
    if model_name not in _model_cache:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install with: uv add sentence-transformers"
            ) from e

        _model_cache[model_name] = SentenceTransformer(model_name)

    return _model_cache[model_name]


class LocalEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using local sentence-transformers models"""

    # Common model dimensions
    MODEL_DIMENSIONS = {
        "all-MiniLM-L6-v2": 384,
        "all-MiniLM-L12-v2": 384,
        "all-mpnet-base-v2": 768,
        "paraphrase-MiniLM-L6-v2": 384,
        "multi-qa-MiniLM-L6-cos-v1": 384,
    }

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
    ):
        """
        Initialize local embedding provider.

        Args:
            model_name: sentence-transformers model name
            device: Device to use ('cpu', 'cuda', 'mps', or None for auto)
        """
        self._model_name = model_name
        self._device = device
        self._model: Optional["SentenceTransformer"] = None
        self._dimensions = self.MODEL_DIMENSIONS.get(model_name)

    def _ensure_model(self) -> "SentenceTransformer":
        """Ensure model is loaded"""
        if self._model is None:
            self._model = _get_model(self._model_name)
            if self._device:
                self._model = self._model.to(self._device)
            # Get actual dimensions from model
            self._dimensions = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            self._ensure_model()
        return self._dimensions or 384

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text"""
        # Run synchronous model in thread pool
        loop = asyncio.get_event_loop()
        vector = await loop.run_in_executor(
            None,
            self._embed_sync,
            text,
        )
        return EmbeddingResult(
            vector=vector,
            model=self._model_name,
            dimensions=len(vector),
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []

        # Run synchronous model in thread pool
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            None,
            self._embed_batch_sync,
            texts,
        )

        results = []
        for vector in vectors:
            results.append(EmbeddingResult(
                vector=vector,
                model=self._model_name,
                dimensions=len(vector),
            ))
        return results

    def _embed_sync(self, text: str) -> list[float]:
        """Synchronous single text embedding"""
        model = self._ensure_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding"""
        model = self._ensure_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]
