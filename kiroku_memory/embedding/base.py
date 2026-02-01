"""Abstract embedding provider interface"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EmbeddingResult:
    """Result from embedding generation"""
    vector: list[float]
    model: str
    dimensions: int
    # Original dimensions before adaptation (if adapted)
    original_dimensions: Optional[int] = None


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'openai', 'local')"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model name being used"""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Native output dimensions of the model"""
        ...

    @abstractmethod
    async def embed_text(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            EmbeddingResult with vector and metadata
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of EmbeddingResult objects
        """
        ...

    def adapt_vector(
        self,
        vector: list[float],
        target_dim: int,
    ) -> list[float]:
        """
        Adapt vector to target dimension by padding or truncating.

        This allows mixing embeddings from different models in the same
        vector index by normalizing to a common dimension.

        Args:
            vector: Original vector
            target_dim: Target dimension

        Returns:
            Adapted vector of target_dim length
        """
        if len(vector) == target_dim:
            return vector
        elif len(vector) > target_dim:
            # Truncate (preserve most significant dimensions)
            return vector[:target_dim]
        else:
            # Pad with zeros
            return vector + [0.0] * (target_dim - len(vector))

    def build_text_for_item(
        self,
        subject: Optional[str],
        predicate: Optional[str],
        obj: Optional[str],
        category: Optional[str],
    ) -> str:
        """
        Build text representation of an item for embedding.

        Args:
            subject: Item subject
            predicate: Item predicate
            obj: Item object
            category: Item category

        Returns:
            Formatted text string
        """
        parts = []
        if subject:
            parts.append(f"Subject: {subject}")
        if predicate:
            parts.append(f"Predicate: {predicate}")
        if obj:
            parts.append(f"Object: {obj}")
        if category:
            parts.append(f"Category: {category}")
        return " | ".join(parts) if parts else "empty"
