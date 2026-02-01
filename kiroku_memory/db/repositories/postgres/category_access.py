"""PostgreSQL implementation of CategoryAccessRepository"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import CategoryAccess
from ...entities import CategoryAccessEntity
from ..base import CategoryAccessRepository


class PostgresCategoryAccessRepository(CategoryAccessRepository):
    """PostgreSQL implementation using SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, model: CategoryAccess) -> CategoryAccessEntity:
        """Convert SQLAlchemy model to domain entity"""
        return CategoryAccessEntity(
            id=model.id,
            category=model.category,
            accessed_at=model.accessed_at,
            source=model.source,
        )

    def _to_model(self, entity: CategoryAccessEntity) -> CategoryAccess:
        """Convert domain entity to SQLAlchemy model"""
        return CategoryAccess(
            id=entity.id,
            category=entity.category,
            accessed_at=entity.accessed_at,
            source=entity.source,
        )

    async def create(self, entity: CategoryAccessEntity) -> UUID:
        """Log a category access"""
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def get_recent(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[CategoryAccessEntity]:
        """Get recent accesses"""
        query = (
            select(CategoryAccess)
            .order_by(CategoryAccess.accessed_at.desc())
            .limit(limit)
        )
        if category:
            query = query.where(CategoryAccess.category == category)
        if since:
            query = query.where(CategoryAccess.accessed_at > since)

        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_category(
        self,
        since: Optional[datetime] = None,
    ) -> dict[str, int]:
        """Count accesses per category"""
        query = select(
            CategoryAccess.category,
            func.count(CategoryAccess.id).label("count"),
        ).group_by(CategoryAccess.category)

        if since:
            query = query.where(CategoryAccess.accessed_at > since)

        result = await self._session.execute(query)
        return {row.category: row.count for row in result.all()}

    async def cleanup_old(self, before: datetime) -> int:
        """Delete old access records, return count deleted"""
        result = await self._session.execute(
            delete(CategoryAccess).where(CategoryAccess.accessed_at < before)
        )
        return result.rowcount or 0
