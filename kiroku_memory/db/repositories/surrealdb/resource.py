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

    def _to_entity(self, record: dict) -> ResourceEntity:
        """Convert SurrealDB record to domain entity"""
        # SurrealDB returns ID as 'resource:uuid-string'
        record_id = record.get("id", "")
        if isinstance(record_id, str) and ":" in record_id:
            uuid_str = record_id.split(":", 1)[1]
        else:
            uuid_str = str(record_id)

        return ResourceEntity(
            id=UUID(uuid_str),
            created_at=datetime.fromisoformat(record["created_at"]) if isinstance(record.get("created_at"), str) else record.get("created_at", datetime.utcnow()),
            source=record.get("source", ""),
            content=record.get("content", ""),
            metadata=record.get("metadata", {}),
        )

    async def create(self, entity: ResourceEntity) -> UUID:
        """Create a new resource, return its ID"""
        # Use specific record ID format: resource:uuid
        record_id = f"resource:{entity.id}"

        result = await self._client.query(
            """
            CREATE $id CONTENT {
                created_at: $created_at,
                source: $source,
                content: $content,
                metadata: $metadata
            }
            """,
            {
                "id": record_id,
                "created_at": entity.created_at.isoformat(),
                "source": entity.source,
                "content": entity.content,
                "metadata": entity.metadata,
            },
        )

        return entity.id

    async def get(self, resource_id: UUID) -> Optional[ResourceEntity]:
        """Get resource by ID"""
        record_id = f"resource:{resource_id}"

        result = await self._client.query(
            "SELECT * FROM $id",
            {"id": record_id},
        )

        # SurrealDB returns list of results per query
        if result and result[0]:
            return self._to_entity(result[0][0])
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

        if result and result[0]:
            return [self._to_entity(r) for r in result[0]]
        return []
