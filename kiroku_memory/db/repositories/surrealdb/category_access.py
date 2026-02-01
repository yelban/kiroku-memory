"""SurrealDB implementation of CategoryAccessRepository"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from ...entities import CategoryAccessEntity
from ..base import CategoryAccessRepository

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealCategoryAccessRepository(CategoryAccessRepository):
    """SurrealDB implementation using SurrealQL"""

    def __init__(self, client: "AsyncSurreal"):
        self._client = client

    def _parse_record_id(self, record_id: str | dict) -> UUID:
        """Extract UUID from SurrealDB record ID"""
        if isinstance(record_id, dict):
            record_id = record_id.get("id", "")
        if isinstance(record_id, str) and ":" in record_id:
            return UUID(record_id.split(":", 1)[1])
        return UUID(str(record_id))

    def _to_entity(self, record: dict) -> CategoryAccessEntity:
        """Convert SurrealDB record to domain entity"""
        access_id = self._parse_record_id(record.get("id", ""))

        accessed_at = record.get("accessed_at")
        if isinstance(accessed_at, str):
            accessed_at = datetime.fromisoformat(accessed_at.replace("Z", "+00:00"))
        elif accessed_at is None:
            accessed_at = datetime.utcnow()

        return CategoryAccessEntity(
            id=access_id,
            category=record.get("category", ""),
            accessed_at=accessed_at,
            source=record.get("source", "context"),
        )

    async def create(self, entity: CategoryAccessEntity) -> UUID:
        """Log a category access"""
        record_id = f"category_access:{entity.id}"

        await self._client.query(
            """
            CREATE $id CONTENT {
                category: $category,
                accessed_at: $accessed_at,
                source: $source
            }
            """,
            {
                "id": record_id,
                "category": entity.category,
                "accessed_at": entity.accessed_at.isoformat(),
                "source": entity.source,
            },
        )

        return entity.id

    async def get_recent(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[CategoryAccessEntity]:
        """Get recent accesses"""
        conditions = []
        params = {"limit": limit}

        if category:
            conditions.append("category = $category")
            params["category"] = category

        if since:
            conditions.append("accessed_at > $since")
            params["since"] = since.isoformat()

        where_clause = ""
        if conditions:
            where_clause = f"WHERE {' AND '.join(conditions)}"

        result = await self._client.query(
            f"""
            SELECT * FROM category_access
            {where_clause}
            ORDER BY accessed_at DESC
            LIMIT $limit
            """,
            params,
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def count_by_category(
        self,
        since: Optional[datetime] = None,
    ) -> dict[str, int]:
        """Count accesses per category"""
        params = {}
        where_clause = ""

        if since:
            where_clause = "WHERE accessed_at > $since"
            params["since"] = since.isoformat()

        result = await self._client.query(
            f"""
            SELECT category, count() as count
            FROM category_access
            {where_clause}
            GROUP BY category
            """,
            params,
        )

        counts = {}
        if result:
            for row in result:
                cat = row.get("category", "")
                cnt = row.get("count", 0)
                counts[cat] = cnt

        return counts

    async def cleanup_old(self, before: datetime) -> int:
        """Delete old access records, return count deleted"""
        # First count
        count_result = await self._client.query(
            "SELECT count() FROM category_access WHERE accessed_at < $before GROUP ALL",
            {"before": before.isoformat()},
        )

        count = 0
        if count_result:
            count = count_result[0].get("count", 0)

        # Then delete
        await self._client.query(
            "DELETE FROM category_access WHERE accessed_at < $before",
            {"before": before.isoformat()},
        )

        return count
