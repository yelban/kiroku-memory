"""PostgreSQL implementation of ResourceRepository"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timedelta

from ...models import Resource, Item
from ...entities import ResourceEntity
from ..base import ResourceRepository


class PostgresResourceRepository(ResourceRepository):
    """PostgreSQL implementation using SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, model: Resource) -> ResourceEntity:
        """Convert SQLAlchemy model to domain entity"""
        return ResourceEntity(
            id=model.id,
            created_at=model.created_at,
            source=model.source,
            content=model.content,
            metadata=model.metadata_ or {},
        )

    def _to_model(self, entity: ResourceEntity) -> Resource:
        """Convert domain entity to SQLAlchemy model"""
        return Resource(
            id=entity.id,
            created_at=entity.created_at,
            source=entity.source,
            content=entity.content,
            metadata_=entity.metadata,
        )

    async def create(self, entity: ResourceEntity) -> UUID:
        """Create a new resource, return its ID"""
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def get(self, resource_id: UUID) -> Optional[ResourceEntity]:
        """Get resource by ID"""
        result = await self._session.execute(
            select(Resource).where(Resource.id == resource_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(
        self,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[ResourceEntity]:
        """List resources with optional filters"""
        query = select(Resource).order_by(Resource.created_at.desc()).limit(limit)

        if source:
            query = query.where(Resource.source == source)
        if since:
            query = query.where(Resource.created_at > since)

        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(self) -> int:
        """Count total resources"""
        result = await self._session.execute(select(func.count(Resource.id)))
        return result.scalar() or 0

    async def delete_orphaned(self, max_age_days: int) -> int:
        """Delete resources older than max_age_days with no associated items"""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        # Find resources without items
        subquery = select(Item.resource_id).where(Item.resource_id.isnot(None))
        result = await self._session.execute(
            delete(Resource).where(
                and_(
                    ~Resource.id.in_(subquery),
                    Resource.created_at < cutoff,
                )
            )
        )
        return result.rowcount or 0

    async def list_unextracted(self, limit: int = 100) -> list[ResourceEntity]:
        """List resources that haven't been extracted yet (no associated items)"""
        subquery = select(Item.resource_id).where(Item.resource_id.isnot(None))
        result = await self._session.execute(
            select(Resource)
            .where(~Resource.id.in_(subquery))
            .order_by(Resource.created_at.desc())
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
