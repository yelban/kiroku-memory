"""PostgreSQL implementation of GraphRepository"""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import GraphEdge
from ...entities import GraphEdgeEntity
from ..base import GraphRepository


class PostgresGraphRepository(GraphRepository):
    """PostgreSQL implementation using SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, model: GraphEdge) -> GraphEdgeEntity:
        """Convert SQLAlchemy model to domain entity"""
        return GraphEdgeEntity(
            id=model.id,
            subject=model.subject,
            predicate=model.predicate,
            object=model.object,
            weight=model.weight,
            created_at=model.created_at,
        )

    def _to_model(self, entity: GraphEdgeEntity) -> GraphEdge:
        """Convert domain entity to SQLAlchemy model"""
        return GraphEdge(
            id=entity.id,
            subject=entity.subject,
            predicate=entity.predicate,
            object=entity.object,
            weight=entity.weight,
            created_at=entity.created_at,
        )

    async def create(self, entity: GraphEdgeEntity) -> UUID:
        """Create a graph edge"""
        model = self._to_model(entity)
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def create_many(self, entities: Sequence[GraphEdgeEntity]) -> list[UUID]:
        """Create multiple edges"""
        models = [self._to_model(e) for e in entities]
        self._session.add_all(models)
        await self._session.flush()
        return [m.id for m in models]

    async def get_by_subject(self, subject: str) -> list[GraphEdgeEntity]:
        """Get all edges from a subject"""
        result = await self._session.execute(
            select(GraphEdge)
            .where(GraphEdge.subject == subject)
            .order_by(GraphEdge.weight.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_object(self, obj: str) -> list[GraphEdgeEntity]:
        """Get all edges to an object"""
        result = await self._session.execute(
            select(GraphEdge)
            .where(GraphEdge.object == obj)
            .order_by(GraphEdge.weight.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_neighbors(self, entity: str, depth: int = 1) -> list[GraphEdgeEntity]:
        """Get edges within N hops of an entity"""
        # For depth=1, get direct neighbors
        result = await self._session.execute(
            select(GraphEdge)
            .where(
                or_(
                    GraphEdge.subject == entity,
                    GraphEdge.object == entity,
                )
            )
            .order_by(GraphEdge.weight.desc())
        )
        edges = [self._to_entity(m) for m in result.scalars().all()]

        if depth <= 1:
            return edges

        # For deeper traversal, recursively expand
        visited_entities = {entity}
        all_edges = list(edges)

        for _ in range(depth - 1):
            # Get new entities from current edges
            new_entities = set()
            for edge in all_edges:
                new_entities.add(edge.subject)
                new_entities.add(edge.object)
            new_entities -= visited_entities

            if not new_entities:
                break

            visited_entities.update(new_entities)

            # Get edges for new entities
            result = await self._session.execute(
                select(GraphEdge)
                .where(
                    or_(
                        GraphEdge.subject.in_(new_entities),
                        GraphEdge.object.in_(new_entities),
                    )
                )
            )
            new_edges = [self._to_entity(m) for m in result.scalars().all()]
            all_edges.extend(new_edges)

        return all_edges

    async def delete_by_subject(self, subject: str) -> int:
        """Delete all edges from a subject, return count deleted"""
        result = await self._session.execute(
            delete(GraphEdge).where(GraphEdge.subject == subject)
        )
        return result.rowcount or 0
