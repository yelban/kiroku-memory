"""SurrealDB implementation of ItemRepository"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Sequence
from uuid import UUID

from ...entities import ItemEntity
from ..base import ItemRepository

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealItemRepository(ItemRepository):
    """SurrealDB implementation using SurrealQL"""

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
        # Handle string format 'table:uuid' or 'table:⟨uuid⟩'
        if isinstance(record_id, str) and ":" in record_id:
            uuid_part = record_id.split(":", 1)[1]
            uuid_part = uuid_part.strip("⟨⟩<>")
            return UUID(uuid_part)
        return UUID(str(record_id))

    def _to_entity(self, record: dict) -> ItemEntity:
        """Convert SurrealDB record to domain entity"""
        item_id = self._parse_record_id(record.get("id", ""))

        # Handle resource reference (record<resource> or RecordID)
        resource_id = None
        resource_ref = record.get("resource")
        if resource_ref:
            if hasattr(resource_ref, "id") and hasattr(resource_ref, "table_name"):
                resource_id = UUID(str(resource_ref.id))
            elif isinstance(resource_ref, str) and ":" in resource_ref:
                uuid_part = resource_ref.split(":", 1)[1].strip("⟨⟩<>")
                resource_id = UUID(uuid_part)
            elif isinstance(resource_ref, dict) and "id" in resource_ref:
                resource_id = self._parse_record_id(resource_ref["id"])

        # Handle supersedes reference
        supersedes = None
        supersedes_ref = record.get("supersedes")
        if supersedes_ref:
            if hasattr(supersedes_ref, "id") and hasattr(supersedes_ref, "table_name"):
                supersedes = UUID(str(supersedes_ref.id))
            elif isinstance(supersedes_ref, str) and ":" in supersedes_ref:
                uuid_part = supersedes_ref.split(":", 1)[1].strip("⟨⟩<>")
                supersedes = UUID(uuid_part)

        # Handle datetime
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

    async def create(self, entity: ItemEntity) -> UUID:
        """Create a single item, return its ID"""
        uuid_str = str(entity.id)

        # Build content with proper record ID references
        resource_ref = None
        if entity.resource_id:
            resource_ref = str(entity.resource_id)

        supersedes_ref = None
        if entity.supersedes:
            supersedes_ref = str(entity.supersedes)

        query = """
            CREATE item CONTENT {
                id: type::thing("item", $uuid),
                created_at: time::now(),
                subject: $subject,
                predicate: $predicate,
                object: $object,
                category: $category,
                confidence: $confidence,
                status: $status,
                resource: IF $resource_id != NONE THEN type::thing("resource", $resource_id) ELSE NONE END,
                supersedes: IF $supersedes_id != NONE THEN type::thing("item", $supersedes_id) ELSE NONE END,
                embedding: $embedding
            }
        """

        await self._client.query(
            query,
            {
                "uuid": uuid_str,
                "subject": entity.subject,
                "predicate": entity.predicate,
                "object": entity.object,
                "category": entity.category,
                "confidence": entity.confidence,
                "status": entity.status,
                "resource_id": resource_ref,
                "supersedes_id": supersedes_ref,
                "embedding": entity.embedding,
            },
        )

        return entity.id

    async def create_many(self, entities: Sequence[ItemEntity]) -> list[UUID]:
        """Create multiple items, return their IDs"""
        ids = []
        for entity in entities:
            item_id = await self.create(entity)
            ids.append(item_id)
        return ids

    async def get(self, item_id: UUID) -> Optional[ItemEntity]:
        """Get item by ID"""
        from surrealdb import RecordID

        record_id = RecordID("item", str(item_id))
        result = await self._client.select(record_id)

        if result:
            return self._to_entity(result[0])
        return None

    async def update(self, entity: ItemEntity) -> None:
        """Update an existing item"""
        record_id = f"item:{entity.id}"

        content = {
            "subject": entity.subject,
            "predicate": entity.predicate,
            "object": entity.object,
            "category": entity.category,
            "confidence": entity.confidence,
            "status": entity.status,
        }

        if entity.supersedes:
            content["supersedes"] = f"item:{entity.supersedes}"

        await self._client.query(
            "UPDATE $id MERGE $content",
            {"id": record_id, "content": content},
        )

    async def update_status(self, item_id: UUID, status: str) -> None:
        """Update item status"""
        record_id = f"item:{item_id}"

        await self._client.query(
            "UPDATE $id SET status = $status",
            {"id": record_id, "status": status},
        )

    async def list(
        self,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 100,
    ) -> list[ItemEntity]:
        """List items with optional filters"""
        conditions = ["status = $status"]
        params = {"status": status, "limit": limit}

        if category:
            conditions.append("category = $category")
            params["category"] = category

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT * FROM item
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT $limit
        """

        result = await self._client.query(query, params)

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def list_by_resource(self, resource_id: UUID) -> list[ItemEntity]:
        """List all items from a specific resource"""
        resource_ref = f"resource:{resource_id}"

        result = await self._client.query(
            """
            SELECT * FROM item
            WHERE resource = $resource_ref
            ORDER BY created_at DESC
            """,
            {"resource_ref": resource_ref},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def list_by_subject(self, subject: str, status: str = "active") -> list[ItemEntity]:
        """List items with matching subject"""
        result = await self._client.query(
            """
            SELECT * FROM item
            WHERE subject = $subject AND status = $status
            ORDER BY created_at DESC
            """,
            {"subject": subject, "status": status},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def count(
        self,
        category: Optional[str] = None,
        status: str = "active",
    ) -> int:
        """Count items with optional filters"""
        conditions = ["status = $status"]
        params = {"status": status}

        if category:
            conditions.append("category = $category")
            params["category"] = category

        where_clause = " AND ".join(conditions)

        result = await self._client.query(
            f"SELECT count() FROM item WHERE {where_clause} GROUP ALL",
            params,
        )

        if result:
            return result[0].get("count", 0)
        return 0

    async def find_potential_conflicts(
        self,
        subject: str,
        predicate: str,
        exclude_id: Optional[UUID] = None,
    ) -> list[ItemEntity]:
        """Find items that may conflict with given subject/predicate"""
        params = {
            "subject": subject,
            "predicate": predicate,
        }

        exclude_clause = ""
        if exclude_id:
            exclude_clause = "AND id != $exclude_id"
            params["exclude_id"] = f"item:{exclude_id}"

        result = await self._client.query(
            f"""
            SELECT * FROM item
            WHERE subject = $subject
                AND predicate = $predicate
                AND status = 'active'
                {exclude_clause}
            """,
            params,
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def list_duplicates(self) -> list[tuple[ItemEntity, ItemEntity]]:
        """Find duplicate items (same subject/predicate/object)"""
        result = await self._client.query(
            """
            SELECT * FROM item
            WHERE status = 'active'
            ORDER BY subject, predicate, object, created_at
            """,
            {},
        )

        if not result:
            return []

        duplicates = []
        seen = {}
        for record in result:
            entity = self._to_entity(record)
            key = (entity.subject, entity.predicate, entity.object)
            if key in seen:
                duplicates.append((seen[key], entity))
            else:
                seen[key] = entity
        return duplicates

    async def count_by_subject_recent(self, subject: str, days: int) -> int:
        """Count items with given subject created in last N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self._client.query(
            """
            SELECT count() FROM item
            WHERE subject = $subject
                AND created_at > $cutoff
                AND status = 'active'
            GROUP ALL
            """,
            {"subject": subject, "cutoff": cutoff.isoformat()},
        )

        if result:
            return result[0].get("count", 0)
        return 0

    async def list_distinct_categories(self, status: str = "active") -> list[str]:
        """List distinct category names for items with given status"""
        result = await self._client.query(
            """
            SELECT category FROM item
            WHERE status = $status AND category IS NOT NONE
            GROUP BY category
            """,
            {"status": status},
        )

        if result:
            return [r.get("category") for r in result if r.get("category")]
        return []

    async def list_old_low_confidence(
        self, max_age_days: int, min_confidence: float
    ) -> list[ItemEntity]:
        """List items older than max_age_days with confidence below min_confidence"""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        result = await self._client.query(
            """
            SELECT * FROM item
            WHERE status = 'active'
                AND created_at < $cutoff
                AND confidence < $min_confidence
            """,
            {"cutoff": cutoff.isoformat(), "min_confidence": min_confidence},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def get_stats_by_status(self) -> dict[str, int]:
        """Get item counts grouped by status"""
        stats = {}
        for status in ["active", "archived", "deleted"]:
            result = await self._client.query(
                "SELECT count() FROM item WHERE status = $status GROUP ALL",
                {"status": status},
            )
            stats[status] = result[0].get("count", 0) if result else 0
        return stats

    async def get_avg_confidence(self, status: str = "active") -> float:
        """Get average confidence for items with given status"""
        result = await self._client.query(
            """
            SELECT math::mean(confidence) AS avg FROM item
            WHERE status = $status
            GROUP ALL
            """,
            {"status": status},
        )

        if result:
            return round(result[0].get("avg", 0.0) or 0.0, 3)
        return 0.0

    async def list_all_ids(self, status: str = "active") -> list[UUID]:
        """List all item IDs with given status"""
        result = await self._client.query(
            "SELECT id FROM item WHERE status = $status",
            {"status": status},
        )

        if result:
            return [self._parse_record_id(r.get("id")) for r in result]
        return []

    async def list_archived(self, limit: int = 100) -> list[ItemEntity]:
        """List archived items"""
        result = await self._client.query(
            """
            SELECT * FROM item
            WHERE status = 'archived'
            ORDER BY created_at DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def get_superseding_item(self, archived_id: UUID) -> Optional[ItemEntity]:
        """Get the active item that supersedes an archived item"""
        result = await self._client.query(
            """
            SELECT * FROM item
            WHERE supersedes = $archived_id AND status = 'active'
            LIMIT 1
            """,
            {"archived_id": f"item:{archived_id}"},
        )

        if result:
            return self._to_entity(result[0])
        return None
