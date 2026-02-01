"""PostgreSQL implementation of ItemRepository"""

from __future__ import annotations

from typing import Optional, Sequence
from uuid import UUID

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, update, and_
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

    async def list_duplicates(self) -> list[tuple[ItemEntity, ItemEntity]]:
        """Find duplicate items (same subject/predicate/object)"""
        query = (
            select(Item)
            .where(Item.status == "active")
            .order_by(Item.subject, Item.predicate, Item.object, Item.created_at)
        )
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        duplicates = []
        seen = {}
        for item in items:
            key = (item.subject, item.predicate, item.object)
            if key in seen:
                duplicates.append((self._to_entity(seen[key]), self._to_entity(item)))
            else:
                seen[key] = item
        return duplicates

    async def count_by_subject_recent(self, subject: str, days: int) -> int:
        """Count items with given subject created in last N days"""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        result = await self._session.execute(
            select(func.count(Item.id)).where(
                and_(
                    Item.subject == subject,
                    Item.created_at > cutoff,
                    Item.status == "active",
                )
            )
        )
        return result.scalar() or 0

    async def list_distinct_categories(self, status: str = "active") -> list[str]:
        """List distinct category names for items with given status"""
        result = await self._session.execute(
            select(Item.category)
            .where(Item.status == status)
            .where(Item.category.isnot(None))
            .distinct()
        )
        return [row[0] for row in result.all()]

    async def list_old_low_confidence(
        self, max_age_days: int, min_confidence: float
    ) -> list[ItemEntity]:
        """List items older than max_age_days with confidence below min_confidence"""
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=max_age_days)
        result = await self._session.execute(
            select(Item).where(
                and_(
                    Item.status == "active",
                    Item.created_at < cutoff,
                    Item.confidence < min_confidence,
                )
            )
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_stats_by_status(self) -> dict[str, int]:
        """Get item counts grouped by status"""
        stats = {}
        for status in ["active", "archived", "deleted"]:
            result = await self._session.execute(
                select(func.count(Item.id)).where(Item.status == status)
            )
            stats[status] = result.scalar() or 0
        return stats

    async def get_avg_confidence(self, status: str = "active") -> float:
        """Get average confidence for items with given status"""
        result = await self._session.execute(
            select(func.avg(Item.confidence)).where(Item.status == status)
        )
        return round(result.scalar() or 0.0, 3)

    async def list_all_ids(self, status: str = "active") -> list[UUID]:
        """List all item IDs with given status"""
        result = await self._session.execute(
            select(Item.id).where(Item.status == status)
        )
        return [row[0] for row in result.all()]

    async def list_archived(self, limit: int = 100) -> list[ItemEntity]:
        """List archived items"""
        result = await self._session.execute(
            select(Item)
            .where(Item.status == "archived")
            .order_by(Item.created_at.desc())
            .limit(limit)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_superseding_item(self, archived_id: UUID) -> Optional[ItemEntity]:
        """Get the active item that supersedes an archived item"""
        result = await self._session.execute(
            select(Item).where(
                and_(
                    Item.supersedes == archived_id,
                    Item.status == "active",
                )
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
