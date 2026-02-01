"""PostgreSQL implementation of EmbeddingRepository using pgvector"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Item, Embedding
from ...entities import ItemEntity, EmbeddingSearchResult
from ..base import EmbeddingRepository


class PostgresEmbeddingRepository(EmbeddingRepository):
    """PostgreSQL implementation using pgvector"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _item_to_entity(self, model: Item) -> ItemEntity:
        """Convert Item model to entity"""
        return ItemEntity(
            id=model.id,
            created_at=model.created_at,
            resource_id=model.resource_id,
            subject=model.subject,
            predicate=model.predicate,
            object=model.object,
            category=model.category,
            confidence=model.confidence,
            status=model.status,
            supersedes=model.supersedes,
        )

    async def upsert(self, item_id: UUID, vector: list[float]) -> None:
        """Insert or update embedding for an item"""
        existing = await self._session.execute(
            select(Embedding).where(Embedding.item_id == item_id)
        )
        if existing.scalar_one_or_none():
            await self._session.execute(
                text("UPDATE embeddings SET embedding = :vec WHERE item_id = :id"),
                {"vec": str(vector), "id": str(item_id)},
            )
        else:
            embedding = Embedding(item_id=item_id, embedding=vector)
            self._session.add(embedding)

    async def get(self, item_id: UUID) -> Optional[list[float]]:
        """Get embedding vector for an item"""
        result = await self._session.execute(
            select(Embedding).where(Embedding.item_id == item_id)
        )
        model = result.scalar_one_or_none()
        if model and model.embedding:
            return list(model.embedding)
        return None

    async def delete(self, item_id: UUID) -> None:
        """Delete embedding for an item"""
        await self._session.execute(
            delete(Embedding).where(Embedding.item_id == item_id)
        )

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        min_similarity: float = 0.5,
        status_filter: str = "active",
    ) -> list[EmbeddingSearchResult]:
        """Search for similar items by vector using pgvector cosine similarity"""
        query_vec_str = str(query_vector)

        # Cosine similarity search using pgvector
        sql = text("""
            SELECT
                i.id, i.created_at, i.resource_id, i.subject, i.predicate,
                i.object, i.category, i.confidence, i.status, i.supersedes,
                1 - (e.embedding <=> :query_vec::vector) as similarity
            FROM items i
            JOIN embeddings e ON i.id = e.item_id
            WHERE i.status = :status
              AND 1 - (e.embedding <=> :query_vec::vector) >= :min_sim
            ORDER BY similarity DESC
            LIMIT :limit
        """)

        result = await self._session.execute(
            sql,
            {
                "query_vec": query_vec_str,
                "status": status_filter,
                "min_sim": min_similarity,
                "limit": limit,
            },
        )
        rows = result.fetchall()

        # Convert to search results
        results = []
        for row in rows:
            entity = ItemEntity(
                id=row.id,
                created_at=row.created_at,
                resource_id=row.resource_id,
                subject=row.subject,
                predicate=row.predicate,
                object=row.object,
                category=row.category,
                confidence=row.confidence,
                status=row.status,
                supersedes=row.supersedes,
            )
            results.append(EmbeddingSearchResult(item=entity, similarity=row.similarity))

        return results

    async def batch_upsert(self, embeddings: dict[UUID, list[float]]) -> int:
        """Batch insert/update embeddings, return count"""
        count = 0
        for item_id, vector in embeddings.items():
            await self.upsert(item_id, vector)
            count += 1
        return count

    async def count(self) -> int:
        """Count total embeddings"""
        result = await self._session.execute(select(func.count(Embedding.item_id)))
        return result.scalar() or 0

    async def delete_stale(self, active_item_ids: list[UUID]) -> int:
        """Delete embeddings not in active_item_ids list"""
        if not active_item_ids:
            # Delete all embeddings if no active items
            result = await self._session.execute(delete(Embedding))
            return result.rowcount or 0

        result = await self._session.execute(
            delete(Embedding).where(~Embedding.item_id.in_(active_item_ids))
        )
        return result.rowcount or 0
