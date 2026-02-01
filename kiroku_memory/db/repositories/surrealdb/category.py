"""SurrealDB implementation of CategoryRepository"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from ...entities import CategoryEntity
from ..base import CategoryRepository

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealCategoryRepository(CategoryRepository):
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
        # Handle string format 'table:uuid'
        if isinstance(record_id, str) and ":" in record_id:
            uuid_part = record_id.split(":", 1)[1]
            uuid_part = uuid_part.strip("⟨⟩<>")
            return UUID(uuid_part)
        return UUID(str(record_id))

    def _to_entity(self, record: dict) -> CategoryEntity:
        """Convert SurrealDB record to domain entity"""
        cat_id = self._parse_record_id(record.get("id", ""))

        updated_at = record.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        elif updated_at is None:
            updated_at = datetime.utcnow()

        return CategoryEntity(
            id=cat_id,
            name=record.get("name", ""),
            summary=record.get("summary"),
            updated_at=updated_at,
        )

    async def create(self, entity: CategoryEntity) -> UUID:
        """Create a new category"""
        from datetime import timezone
        from surrealdb import RecordID

        record_id = RecordID("category", str(entity.id))

        # Ensure datetime has timezone for SurrealDB
        updated_at = entity.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        await self._client.query(
            """
            CREATE $id CONTENT {
                name: $name,
                summary: $summary,
                updated_at: $updated_at
            }
            """,
            {
                "id": record_id,
                "name": entity.name,
                "summary": entity.summary,
                "updated_at": updated_at,
            },
        )

        return entity.id

    async def get(self, category_id: UUID) -> Optional[CategoryEntity]:
        """Get category by ID"""
        from surrealdb import RecordID

        record_id = RecordID("category", str(category_id))
        result = await self._client.select(record_id)

        if result:
            return self._to_entity(result[0] if isinstance(result, list) else result)
        return None

    async def get_by_name(self, name: str) -> Optional[CategoryEntity]:
        """Get category by name"""
        result = await self._client.query(
            "SELECT * FROM category WHERE name = $name LIMIT 1",
            {"name": name},
        )

        if result:
            return self._to_entity(result[0])
        return None

    async def list(self) -> list[CategoryEntity]:
        """List all categories"""
        result = await self._client.query(
            "SELECT * FROM category ORDER BY name",
            {},
        )

        if result:
            return [self._to_entity(r) for r in result]
        return []

    async def update_summary(self, name: str, summary: str) -> None:
        """Update category summary"""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        await self._client.query(
            """
            UPDATE category SET
                summary = $summary,
                updated_at = $updated_at
            WHERE name = $name
            """,
            {
                "name": name,
                "summary": summary,
                "updated_at": now,
            },
        )

    async def upsert(self, entity: CategoryEntity) -> UUID:
        """Create or update category by name"""
        from datetime import timezone

        existing = await self.get_by_name(entity.name)

        if existing:
            now = datetime.now(timezone.utc)
            await self._client.query(
                """
                UPDATE category SET
                    summary = $summary,
                    updated_at = $updated_at
                WHERE name = $name
                """,
                {
                    "name": entity.name,
                    "summary": entity.summary,
                    "updated_at": now,
                },
            )
            return existing.id
        else:
            return await self.create(entity)

    async def count_items_per_category(self, status: str = "active") -> dict[str, int]:
        """Count items per category for given status"""
        result = await self._client.query(
            """
            SELECT category, count() as cnt FROM item
            WHERE status = $status AND category IS NOT NONE
            GROUP BY category
            """,
            {"status": status},
        )

        if result:
            return {r.get("category"): r.get("cnt", 0) for r in result if r.get("category")}
        return {}
