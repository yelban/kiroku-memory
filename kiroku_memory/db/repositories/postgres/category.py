"""PostgreSQL implementation of CategoryRepository"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Category, Item
from ...entities import CategoryEntity
from ..base import CategoryRepository


class PostgresCategoryRepository(CategoryRepository):
    """PostgreSQL implementation using SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, model: Category) -> CategoryEntity:
        """Convert SQLAlchemy model to domain entity"""
        return CategoryEntity(
            id=model.id,
            name=model.name,
            summary=model.summary,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: CategoryEntity) -> Category:
        """Convert domain entity to SQLAlchemy model"""
        return Category(
            id=entity.id,
            name=entity.name,
            summary=entity.summary,
            updated_at=entity.updated_at,
        )

    async def create(self, entity: CategoryEntity) -> UUID:
        """Create a new category"""
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def get(self, category_id: UUID) -> Optional[CategoryEntity]:
        """Get category by ID"""
        result = await self._session.execute(
            select(Category).where(Category.id == category_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_name(self, name: str) -> Optional[CategoryEntity]:
        """Get category by name"""
        result = await self._session.execute(
            select(Category).where(Category.name == name)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(self) -> list[CategoryEntity]:
        """List all categories"""
        result = await self._session.execute(
            select(Category).order_by(Category.name)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def update_summary(self, name: str, summary: str) -> None:
        """Update category summary"""
        await self._session.execute(
            update(Category)
            .where(Category.name == name)
            .values(summary=summary, updated_at=datetime.utcnow())
        )

    async def upsert(self, entity: CategoryEntity) -> UUID:
        """Create or update category by name"""
        existing = await self.get_by_name(entity.name)
        if existing:
            await self._session.execute(
                update(Category)
                .where(Category.name == entity.name)
                .values(
                    summary=entity.summary,
                    updated_at=datetime.utcnow(),
                )
            )
            return existing.id
        else:
            return await self.create(entity)

    async def count_items_per_category(self, status: str = "active") -> dict[str, int]:
        """Count items per category for given status"""
        result = await self._session.execute(
            select(Item.category, func.count(Item.id))
            .where(Item.status == status)
            .where(Item.category.isnot(None))
            .group_by(Item.category)
        )
        return {row[0]: row[1] for row in result.all()}
