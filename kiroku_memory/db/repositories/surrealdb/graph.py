"""SurrealDB implementation of GraphRepository"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Sequence
from uuid import UUID

from ...entities import GraphEdgeEntity
from ..base import GraphRepository

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealGraphRepository(GraphRepository):
    """
    SurrealDB implementation using SurrealQL.

    Note: This uses a graph_edge table (string-based subject/object)
    rather than native RELATE (record-based) for compatibility with
    the PostgreSQL schema. For native graph traversal with items,
    use the relates_to relation table directly.
    """

    def __init__(self, client: "AsyncSurreal"):
        self._client = client

    def _parse_record_id(self, record_id: str | dict) -> UUID:
        """Extract UUID from SurrealDB record ID"""
        if isinstance(record_id, dict):
            record_id = record_id.get("id", "")
        if isinstance(record_id, str) and ":" in record_id:
            return UUID(record_id.split(":", 1)[1])
        return UUID(str(record_id))

    def _to_entity(self, record: dict) -> GraphEdgeEntity:
        """Convert SurrealDB record to domain entity"""
        edge_id = self._parse_record_id(record.get("id", ""))

        created_at = record.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.utcnow()

        return GraphEdgeEntity(
            id=edge_id,
            subject=record.get("subject", ""),
            predicate=record.get("predicate", ""),
            object=record.get("object", ""),
            weight=float(record.get("weight", 1.0)),
            created_at=created_at,
        )

    async def _ensure_table_exists(self) -> None:
        """Ensure graph_edge table exists (idempotent)"""
        await self._client.query(
            """
            DEFINE TABLE IF NOT EXISTS graph_edge SCHEMAFULL;
            DEFINE FIELD IF NOT EXISTS subject ON graph_edge TYPE string;
            DEFINE FIELD IF NOT EXISTS predicate ON graph_edge TYPE string;
            DEFINE FIELD IF NOT EXISTS object ON graph_edge TYPE string;
            DEFINE FIELD IF NOT EXISTS weight ON graph_edge TYPE float DEFAULT 1.0;
            DEFINE FIELD IF NOT EXISTS created_at ON graph_edge TYPE datetime DEFAULT time::now();
            DEFINE INDEX IF NOT EXISTS idx_edge_subject ON graph_edge FIELDS subject;
            DEFINE INDEX IF NOT EXISTS idx_edge_object ON graph_edge FIELDS object;
            """,
            {},
        )

    async def create(self, entity: GraphEdgeEntity) -> UUID:
        """Create a graph edge"""
        record_id = f"graph_edge:{entity.id}"

        await self._client.query(
            """
            CREATE $id CONTENT {
                subject: $subject,
                predicate: $predicate,
                object: $object,
                weight: $weight,
                created_at: $created_at
            }
            """,
            {
                "id": record_id,
                "subject": entity.subject,
                "predicate": entity.predicate,
                "object": entity.object,
                "weight": entity.weight,
                "created_at": entity.created_at.isoformat(),
            },
        )

        return entity.id

    async def create_many(self, entities: Sequence[GraphEdgeEntity]) -> list[UUID]:
        """Create multiple edges"""
        ids = []
        for entity in entities:
            edge_id = await self.create(entity)
            ids.append(edge_id)
        return ids

    async def get_by_subject(self, subject: str) -> list[GraphEdgeEntity]:
        """Get all edges from a subject"""
        result = await self._client.query(
            """
            SELECT * FROM graph_edge
            WHERE subject = $subject
            ORDER BY weight DESC
            """,
            {"subject": subject},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def get_by_object(self, obj: str) -> list[GraphEdgeEntity]:
        """Get all edges to an object"""
        result = await self._client.query(
            """
            SELECT * FROM graph_edge
            WHERE object = $obj
            ORDER BY weight DESC
            """,
            {"obj": obj},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def get_neighbors(self, entity: str, depth: int = 1) -> list[GraphEdgeEntity]:
        """Get edges within N hops of an entity"""
        # For depth=1, get direct neighbors
        result = await self._client.query(
            """
            SELECT * FROM graph_edge
            WHERE subject = $entity OR object = $entity
            ORDER BY weight DESC
            """,
            {"entity": entity},
        )

        edges = []
        if result:
            edges = [self._to_entity(r) for r in result]

        if depth <= 1:
            return edges

        # For deeper traversal, recursively expand
        visited_entities = {entity}
        all_edges = list(edges)

        for _ in range(depth - 1):
            # Get new entities from current edges
            new_entities = set()
            for edge in all_edges:
                new_entities.add(edge.subject)
                new_entities.add(edge.object)
            new_entities -= visited_entities

            if not new_entities:
                break

            visited_entities.update(new_entities)

            # Get edges for new entities
            entities_list = list(new_entities)
            result = await self._client.query(
                """
                SELECT * FROM graph_edge
                WHERE subject IN $entities OR object IN $entities
                """,
                {"entities": entities_list},
            )

            if result:
                new_edges = [self._to_entity(r) for r in result]
                all_edges.extend(new_edges)

        return all_edges

    async def delete_by_subject(self, subject: str) -> int:
        """Delete all edges from a subject, return count deleted"""
        # First count
        count_result = await self._client.query(
            "SELECT count() FROM graph_edge WHERE subject = $subject GROUP ALL",
            {"subject": subject},
        )

        count = 0
        if count_result:
            count = count_result[0].get("count", 0)

        # Then delete
        await self._client.query(
            "DELETE FROM graph_edge WHERE subject = $subject",
            {"subject": subject},
        )

        return count
