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

    def _parse_record_id(self, record_id: str | dict) -> UUID:
        """Extract UUID from SurrealDB record ID"""
        if isinstance(record_id, dict):
            record_id = record_id.get("id", "")
        if isinstance(record_id, str) and ":" in record_id:
            return UUID(record_id.split(":", 1)[1])
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
        record_id = f"category:{entity.id}"

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
                "updated_at": entity.updated_at.isoformat(),
            },
        )

        return entity.id

    async def get(self, category_id: UUID) -> Optional[CategoryEntity]:
        """Get category by ID"""
        record_id = f"category:{category_id}"

        result = await self._client.query(
            "SELECT * FROM $id",
            {"id": record_id},
        )

        if result:
            return self._to_entity(result[0])
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
                "updated_at": datetime.utcnow().isoformat(),
            },
        )

    async def upsert(self, entity: CategoryEntity) -> UUID:
        """Create or update category by name"""
        existing = await self.get_by_name(entity.name)

        if existing:
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
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            return existing.id
        else:
            return await self.create(entity)
