"""PostgreSQL implementation of ResourceRepository"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Resource
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
