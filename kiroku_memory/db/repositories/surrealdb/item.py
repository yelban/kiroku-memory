"""SurrealDB implementation of ItemRepository"""

from __future__ import annotations

from datetime import datetime
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

    def _parse_record_id(self, record_id: str | dict) -> UUID:
        """Extract UUID from SurrealDB record ID (e.g., 'item:uuid-string')"""
        if isinstance(record_id, dict):
            record_id = record_id.get("id", "")
        if isinstance(record_id, str) and ":" in record_id:
            return UUID(record_id.split(":", 1)[1])
        return UUID(str(record_id))

    def _to_entity(self, record: dict) -> ItemEntity:
        """Convert SurrealDB record to domain entity"""
        item_id = self._parse_record_id(record.get("id", ""))

        # Handle resource reference (record<resource>)
        resource_id = None
        resource_ref = record.get("resource")
        if resource_ref:
            if isinstance(resource_ref, str) and ":" in resource_ref:
                resource_id = UUID(resource_ref.split(":", 1)[1])
            elif isinstance(resource_ref, dict) and "id" in resource_ref:
                resource_id = self._parse_record_id(resource_ref["id"])

        # Handle supersedes reference
        supersedes = None
        supersedes_ref = record.get("supersedes")
        if supersedes_ref:
            if isinstance(supersedes_ref, str) and ":" in supersedes_ref:
                supersedes = UUID(supersedes_ref.split(":", 1)[1])

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
        record_id = f"item:{entity.id}"

        content = {
            "created_at": entity.created_at.isoformat(),
            "subject": entity.subject,
            "predicate": entity.predicate,
            "object": entity.object,
            "category": entity.category,
            "confidence": entity.confidence,
            "status": entity.status,
        }

        if entity.resource_id:
            content["resource"] = f"resource:{entity.resource_id}"
        if entity.supersedes:
            content["supersedes"] = f"item:{entity.supersedes}"
        if entity.embedding:
            content["embedding"] = entity.embedding

        await self._client.query(
            "CREATE $id CONTENT $content",
            {"id": record_id, "content": content},
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
        record_id = f"item:{item_id}"

        result = await self._client.query(
            "SELECT * FROM $id",
            {"id": record_id},
        )

        if result and result[0]:
            return self._to_entity(result[0][0])
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

        if result and result[0]:
            return [self._to_entity(r) for r in result[0]]
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

        if result and result[0]:
            return [self._to_entity(r) for r in result[0]]
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

        if result and result[0]:
            return [self._to_entity(r) for r in result[0]]
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

        if result and result[0]:
            return result[0][0].get("count", 0)
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

        if result and result[0]:
            return [self._to_entity(r) for r in result[0]]
        return []
