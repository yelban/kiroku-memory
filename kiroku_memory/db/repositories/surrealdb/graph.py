"""SurrealDB implementation of GraphRepository"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import UUID

from ...entities import GraphEdgeEntity, GraphPath
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
        from datetime import timezone
        from surrealdb import RecordID

        record_id = RecordID("graph_edge", str(entity.id))

        # Ensure datetime has timezone for SurrealDB
        created_at = entity.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

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
                "created_at": created_at,
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

    async def find_paths(
        self,
        source: str,
        target: Optional[str] = None,
        max_depth: int = 2,
        max_paths: int = 20,
    ) -> list[GraphPath]:
        """BFS find paths from source."""
        max_depth = min(max_depth, 3)
        paths: list[GraphPath] = []
        queue: deque[tuple[str, list[str], list[GraphEdgeEntity], float]] = deque()
        queue.append((source, [source], [], 1.0))
        visited_edges: set[tuple[str, str, str]] = set()

        while queue:
            entity, hops, path_edges, w = queue.popleft()
            if len(hops) - 1 >= max_depth:
                continue

            result = await self._client.query(
                """
                SELECT * FROM graph_edge
                WHERE subject = $entity OR object = $entity
                """,
                {"entity": entity},
            )
            neighbors = [self._to_entity(r) for r in result] if result else []

            for edge in neighbors:
                edge_triple = (edge.subject, edge.predicate, edge.object)
                if edge_triple in visited_edges:
                    continue
                visited_edges.add(edge_triple)

                next_entity = edge.object if edge.subject == entity else edge.subject
                if next_entity in hops:
                    continue

                new_hops = hops + [next_entity]
                new_edges = path_edges + [edge]
                new_weight = w * edge.weight

                paths.append(GraphPath(
                    source=source,
                    target=next_entity,
                    edges=new_edges,
                    hops=new_hops,
                    distance=len(new_edges),
                    weight=new_weight,
                ))

                if len(new_hops) - 1 < max_depth:
                    queue.append((next_entity, new_hops, new_edges, new_weight))

        paths.sort(key=lambda p: p.weight, reverse=True)

        if target:
            paths = [p for p in paths if p.target == target]

        return paths[:max_paths]

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

    async def list_all(self) -> list[GraphEdgeEntity]:
        """List all graph edges"""
        result = await self._client.query(
            "SELECT * FROM graph_edge ORDER BY weight DESC",
            {},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def delete_all(self) -> int:
        """Delete all edges, return count deleted"""
        # First count
        count_result = await self._client.query(
            "SELECT count() FROM graph_edge GROUP ALL",
            {},
        )

        count = count_result[0].get("count", 0) if count_result else 0

        # Then delete
        await self._client.query("DELETE FROM graph_edge", {})

        return count

    async def update_weight(
        self, subject: str, predicate: str, obj: str, weight: float
    ) -> bool:
        """Update edge weight, return True if updated"""
        # Check if exists first
        check_result = await self._client.query(
            """
            SELECT count() FROM graph_edge
            WHERE subject = $subject
                AND predicate = $predicate
                AND object = $obj
            GROUP ALL
            """,
            {"subject": subject, "predicate": predicate, "obj": obj},
        )

        exists = check_result[0].get("count", 0) > 0 if check_result else False

        if exists:
            await self._client.query(
                """
                UPDATE graph_edge SET weight = $weight
                WHERE subject = $subject
                    AND predicate = $predicate
                    AND object = $obj
                """,
                {"subject": subject, "predicate": predicate, "obj": obj, "weight": weight},
            )
            return True
        return False

    async def count(self) -> int:
        """Count total edges"""
        result = await self._client.query(
            "SELECT count() FROM graph_edge GROUP ALL",
            {},
        )

        if result:
            return result[0].get("count", 0)
        return 0
