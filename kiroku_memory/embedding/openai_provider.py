"""OpenAI embedding provider"""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from .base import EmbeddingProvider, EmbeddingResult


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API"""

    # Default model dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        dimensions: Optional[int] = None,
    ):
        """
        Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key
            model_name: Model to use (default: text-embedding-3-small)
            dimensions: Override output dimensions (for text-embedding-3 models)
        """
        self._client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name
        self._dimensions = dimensions or self.MODEL_DIMENSIONS.get(model_name, 1536)

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text"""
        response = await self._client.embeddings.create(
            model=self._model_name,
            input=text,
            dimensions=self._dimensions,
        )
        vector = response.data[0].embedding
        return EmbeddingResult(
            vector=vector,
            model=self._model_name,
            dimensions=len(vector),
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._model_name,
            input=texts,
            dimensions=self._dimensions,
        )

        results = []
        for data in response.data:
            results.append(EmbeddingResult(
                vector=data.embedding,
                model=self._model_name,
                dimensions=len(data.embedding),
            ))

        return results
