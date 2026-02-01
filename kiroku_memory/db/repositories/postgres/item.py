"""PostgreSQL implementation of ItemRepository"""

from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Item
from ...entities import ItemEntity
from ..base import ItemRepository


class PostgresItemRepository(ItemRepository):
    """PostgreSQL implementation using SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, model: Item) -> ItemEntity:
        """Convert SQLAlchemy model to domain entity"""
        return ItemEntity(
            id=model.id,
            created_at=model.created_at,
            resource_id=model.resource_id,
            subject=model.subject,
            predicate=model.predicate,
            object=model.object,
            category=model.category,
            confidence=model.confidence,
            status=model.status,
            supersedes=model.supersedes,
        )

    def _to_model(self, entity: ItemEntity) -> Item:
        """Convert domain entity to SQLAlchemy model"""
        return Item(
            id=entity.id,
            created_at=entity.created_at,
            resource_id=entity.resource_id,
            subject=entity.subject,
            predicate=entity.predicate,
            object=entity.object,
            category=entity.category,
            confidence=entity.confidence,
            status=entity.status,
            supersedes=entity.supersedes,
        )

    async def create(self, entity: ItemEntity) -> UUID:
        """Create a single item, return its ID"""
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def create_many(self, entities: Sequence[ItemEntity]) -> list[UUID]:
        """Create multiple items, return their IDs"""
        models = [self._to_model(e) for e in entities]
        self._session.add_all(models)
        await self._session.flush()
        return [m.id for m in models]

    async def get(self, item_id: UUID) -> Optional[ItemEntity]:
        """Get item by ID"""
        result = await self._session.execute(
            select(Item).where(Item.id == item_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def update(self, entity: ItemEntity) -> None:
        """Update an existing item"""
        await self._session.execute(
            update(Item)
            .where(Item.id == entity.id)
            .values(
                subject=entity.subject,
                predicate=entity.predicate,
                object=entity.object,
                category=entity.category,
                confidence=entity.confidence,
                status=entity.status,
                supersedes=entity.supersedes,
            )
        )

    async def update_status(self, item_id: UUID, status: str) -> None:
        """Update item status"""
        await self._session.execute(
            update(Item)
            .where(Item.id == item_id)
            .values(status=status)
        )

    async def list(
        self,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 100,
    ) -> list[ItemEntity]:
        """List items with optional filters"""
        query = (
            select(Item)
            .where(Item.status == status)
            .order_by(Item.created_at.desc())
            .limit(limit)
        )
        if category:
            query = query.where(Item.category == category)

        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_resource(self, resource_id: UUID) -> list[ItemEntity]:
        """List all items from a specific resource"""
        result = await self._session.execute(
            select(Item)
            .where(Item.resource_id == resource_id)
            .order_by(Item.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_subject(self, subject: str, status: str = "active") -> list[ItemEntity]:
        """List items with matching subject"""
        result = await self._session.execute(
            select(Item)
            .where(Item.subject == subject)
            .where(Item.status == status)
            .order_by(Item.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        category: Optional[str] = None,
        status: str = "active",
    ) -> int:
        """Count items with optional filters"""
        query = select(func.count(Item.id)).where(Item.status == status)
        if category:
            query = query.where(Item.category == category)
        result = await self._session.execute(query)
        return result.scalar() or 0

    async def find_potential_conflicts(
        self,
        subject: str,
        predicate: str,
        exclude_id: Optional[UUID] = None,
    ) -> list[ItemEntity]:
        """Find items that may conflict with given subject/predicate"""
        query = (
            select(Item)
            .where(Item.subject == subject)
            .where(Item.predicate == predicate)
            .where(Item.status == "active")
        )
        if exclude_id:
            query = query.where(Item.id != exclude_id)

        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
