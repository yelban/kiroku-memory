"""SurrealDB implementation of ResourceRepository"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from ...entities import ResourceEntity
from ..base import ResourceRepository

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealResourceRepository(ResourceRepository):
    """SurrealDB implementation using SurrealQL"""

    def __init__(self, client: "AsyncSurreal"):
        self._client = client

    def _parse_record_id(self, record_id) -> UUID:
        """Extract UUID from SurrealDB record ID (RecordID object or string)"""
        # Handle RecordID object from surrealdb SDK
        if hasattr(record_id, "id") and hasattr(record_id, "table_name"):
            return UUID(str(record_id.id))
        # Handle string format 'table:uuid'
        if isinstance(record_id, str) and ":" in record_id:
            # Remove angle brackets if present: resource:⟨uuid⟩ -> uuid
            uuid_part = record_id.split(":", 1)[1]
            uuid_part = uuid_part.strip("⟨⟩<>")
            return UUID(uuid_part)
        return UUID(str(record_id))

    def _to_entity(self, record: dict) -> ResourceEntity:
        """Convert SurrealDB record to domain entity"""
        record_id = self._parse_record_id(record.get("id", ""))

        # Handle datetime (may be datetime object or ISO string)
        created_at = record.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif created_at is None:
            created_at = datetime.utcnow()

        return ResourceEntity(
            id=record_id,
            created_at=created_at,
            source=record.get("source", ""),
            content=record.get("content", ""),
            metadata=record.get("metadata", {}),
        )

    async def create(self, entity: ResourceEntity) -> UUID:
        """Create a new resource, return its ID"""
        uuid_str = str(entity.id)

        result = await self._client.query(
            """
            CREATE resource CONTENT {
                id: type::thing("resource", $uuid),
                created_at: time::now(),
                source: $source,
                content: $content,
                metadata: $metadata
            }
            """,
            {
                "uuid": uuid_str,
                "source": entity.source,
                "content": entity.content,
                "metadata": entity.metadata,
            },
        )

        return entity.id

    async def get(self, resource_id: UUID) -> Optional[ResourceEntity]:
        """Get resource by ID"""
        from surrealdb import RecordID

        record_id = RecordID("resource", str(resource_id))
        result = await self._client.select(record_id)

        if result:
            return self._to_entity(result[0])
        return None

    async def list(
        self,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[ResourceEntity]:
        """List resources with optional filters"""
        conditions = []
        params = {"limit": limit}

        if source:
            conditions.append("source = $source")
            params["source"] = source

        if since:
            conditions.append("created_at > $since")
            params["since"] = since.isoformat()

        where_clause = " AND ".join(conditions) if conditions else ""
        if where_clause:
            where_clause = f"WHERE {where_clause}"

        query = f"""
            SELECT * FROM resource
            {where_clause}
            ORDER BY created_at DESC
            LIMIT $limit
        """

        result = await self._client.query(query, params)

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def count(self) -> int:
        """Count total resources"""
        result = await self._client.query(
            "SELECT count() FROM resource GROUP ALL",
            {},
        )

        if result:
            return result[0].get("count", 0)
        return 0

    async def delete_orphaned(self, max_age_days: int) -> int:
        """Delete resources older than max_age_days with no associated items"""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        # First count orphaned resources
        count_result = await self._client.query(
            """
            SELECT count() FROM resource
            WHERE created_at < $cutoff
                AND id NOT IN (SELECT resource FROM item WHERE resource IS NOT NONE)
            GROUP ALL
            """,
            {"cutoff": cutoff.isoformat()},
        )

        count = count_result[0].get("count", 0) if count_result else 0

        # Then delete
        await self._client.query(
            """
            DELETE FROM resource
            WHERE created_at < $cutoff
                AND id NOT IN (SELECT resource FROM item WHERE resource IS NOT NONE)
            """,
            {"cutoff": cutoff.isoformat()},
        )

        return count

    async def list_unextracted(self, limit: int = 100) -> list[ResourceEntity]:
        """List resources that haven't been extracted yet (no associated items)"""
        result = await self._client.query(
            """
            SELECT * FROM resource
            WHERE id NOT IN (SELECT resource FROM item WHERE resource IS NOT NONE)
            ORDER BY created_at DESC
            LIMIT $limit
            """,
            {"limit": limit},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []
