"""SurrealDB implementation of EmbeddingRepository using inline embeddings"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from ...entities import ItemEntity, EmbeddingSearchResult
from ..base import EmbeddingRepository

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealEmbeddingRepository(EmbeddingRepository):
    """
    SurrealDB implementation using inline embeddings on items.

    Unlike PostgreSQL which stores embeddings in a separate table,
    SurrealDB stores embeddings directly on item records with HNSW index.
    """

    def __init__(self, client: "AsyncSurreal"):
        self._client = client

    def _parse_record_id(self, record_id) -> UUID:
        """Extract UUID from SurrealDB record ID (RecordID object or string)"""
        # Handle RecordID object from surrealdb SDK
        if hasattr(record_id, "id") and hasattr(record_id, "table_name"):
            return UUID(str(record_id.id))
        # Handle dict with 'id' key
        if isinstance(record_id, dict):
            return self._parse_record_id(record_id.get("id", ""))
        # Handle string format 'table:uuid'
        if isinstance(record_id, str) and ":" in record_id:
            uuid_part = record_id.split(":", 1)[1]
            uuid_part = uuid_part.strip("⟨⟩<>")
            return UUID(uuid_part)
        return UUID(str(record_id))

    def _to_item_entity(self, record: dict) -> ItemEntity:
        """Convert SurrealDB record to ItemEntity"""
        item_id = self._parse_record_id(record.get("id", ""))

        resource_id = None
        resource_ref = record.get("resource")
        if resource_ref:
            if isinstance(resource_ref, str) and ":" in resource_ref:
                resource_id = UUID(resource_ref.split(":", 1)[1])

        supersedes = None
        supersedes_ref = record.get("supersedes")
        if supersedes_ref:
            if isinstance(supersedes_ref, str) and ":" in supersedes_ref:
                supersedes = UUID(supersedes_ref.split(":", 1)[1])

        created_at = record.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.utcnow()

        return ItemEntity(
            id=item_id,
            created_at=created_at,
            resource_id=resource_id,
            subject=record.get("subject"),
            predicate=record.get("predicate"),
            object=record.get("object"),
            category=record.get("category"),
            confidence=float(record.get("confidence", 1.0)),
            status=record.get("status", "active"),
            supersedes=supersedes,
            embedding=record.get("embedding"),
        )

    async def upsert(self, item_id: UUID, vector: list[float]) -> None:
        """Insert or update embedding for an item"""
        from surrealdb import RecordID

        record_id = RecordID("item", str(item_id))

        await self._client.query(
            """
            UPDATE $id SET
                embedding = $embedding,
                embedding_dim = $dim
            """,
            {
                "id": record_id,
                "embedding": vector,
                "dim": len(vector),
            },
        )

    async def get(self, item_id: UUID) -> Optional[list[float]]:
        """Get embedding vector for an item"""
        from surrealdb import RecordID

        record_id = RecordID("item", str(item_id))
        result = await self._client.select(record_id)

        if result:
            record = result[0] if isinstance(result, list) else result
            return record.get("embedding") if isinstance(record, dict) else None
        return None

    async def delete(self, item_id: UUID) -> None:
        """Delete embedding for an item (set to null)"""
        from surrealdb import RecordID

        record_id = RecordID("item", str(item_id))

        await self._client.query(
            """
            UPDATE $id SET
                embedding = NONE,
                embedding_dim = NONE,
                embedding_model = NONE
            """,
            {"id": record_id},
        )

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        min_similarity: float = 0.5,
        status_filter: str = "active",
    ) -> list[EmbeddingSearchResult]:
        """
        Search for similar items by vector using cosine similarity.

        Uses SurrealDB's vector::similarity::cosine function with HNSW index.
        """
        result = await self._client.query(
            """
            SELECT
                *,
                vector::similarity::cosine(embedding, $query_vec) AS similarity
            FROM item
            WHERE status = $status
                AND embedding IS NOT NONE
                AND vector::similarity::cosine(embedding, $query_vec) >= $min_sim
            ORDER BY similarity DESC
            LIMIT $limit
            """,
            {
                "query_vec": query_vector,
                "status": status_filter,
                "min_sim": min_similarity,
                "limit": limit,
            },
        )

        results = []
        if result:
            for record in result:
                item = self._to_item_entity(record)
                similarity = float(record.get("similarity", 0.0))
                results.append(EmbeddingSearchResult(item=item, similarity=similarity))

        return results

    async def batch_upsert(self, embeddings: dict[UUID, list[float]]) -> int:
        """Batch insert/update embeddings, return count"""
        count = 0
        for item_id, vector in embeddings.items():
            await self.upsert(item_id, vector)
            count += 1
        return count

    async def count(self) -> int:
        """Count total embeddings (items with embedding field set)"""
        result = await self._client.query(
            "SELECT count() FROM item WHERE embedding IS NOT NONE GROUP ALL",
            {},
        )

        if result:
            return result[0].get("count", 0)
        return 0

    async def delete_stale(self, active_item_ids: list[UUID]) -> int:
        """Delete embeddings not in active_item_ids list (set to null)"""
        if not active_item_ids:
            # Clear all embeddings if no active items
            count_result = await self._client.query(
                "SELECT count() FROM item WHERE embedding IS NOT NONE GROUP ALL",
                {},
            )
            count = count_result[0].get("count", 0) if count_result else 0

            await self._client.query(
                "UPDATE item SET embedding = NONE, embedding_dim = NONE WHERE embedding IS NOT NONE",
                {},
            )
            return count

        # Convert UUIDs to record IDs
        from surrealdb import RecordID
        active_ids = [RecordID("item", str(item_id)) for item_id in active_item_ids]

        # Count stale embeddings
        count_result = await self._client.query(
            """
            SELECT count() FROM item
            WHERE embedding IS NOT NONE AND id NOT IN $active_ids
            GROUP ALL
            """,
            {"active_ids": active_ids},
        )
        count = count_result[0].get("count", 0) if count_result else 0

        # Clear stale embeddings
        await self._client.query(
            """
            UPDATE item SET embedding = NONE, embedding_dim = NONE
            WHERE embedding IS NOT NONE AND id NOT IN $active_ids
            """,
            {"active_ids": active_ids},
        )

        return count
