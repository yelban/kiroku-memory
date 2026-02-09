"""PostgreSQL implementation of GraphRepository"""

from __future__ import annotations

from collections import deque
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, delete, or_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import GraphEdge
from ...entities import GraphEdgeEntity, GraphPath
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

    async def find_paths(
        self,
        source: str,
        target: Optional[str] = None,
        max_depth: int = 2,
        max_paths: int = 20,
    ) -> list[GraphPath]:
        """BFS find paths from source."""
        max_depth = min(max_depth, 3)
        paths: list[GraphPath] = []
        queue: deque[tuple[str, list[str], list[GraphEdgeEntity], float]] = deque()
        queue.append((source, [source], [], 1.0))
        visited_edges: set[tuple[str, str, str]] = set()

        while queue:
            entity, hops, path_edges, w = queue.popleft()
            if len(hops) - 1 >= max_depth:
                continue

            result = await self._session.execute(
                select(GraphEdge).where(
                    or_(GraphEdge.subject == entity, GraphEdge.object == entity)
                )
            )
            neighbors = [self._to_entity(m) for m in result.scalars().all()]

            for edge in neighbors:
                edge_triple = (edge.subject, edge.predicate, edge.object)
                if edge_triple in visited_edges:
                    continue
                visited_edges.add(edge_triple)

                next_entity = edge.object if edge.subject == entity else edge.subject
                if next_entity in hops:
                    continue

                new_hops = hops + [next_entity]
                new_edges = path_edges + [edge]
                new_weight = w * edge.weight

                paths.append(GraphPath(
                    source=source,
                    target=next_entity,
                    edges=new_edges,
                    hops=new_hops,
                    distance=len(new_edges),
                    weight=new_weight,
                ))

                if len(new_hops) - 1 < max_depth:
                    queue.append((next_entity, new_hops, new_edges, new_weight))

        paths.sort(key=lambda p: p.weight, reverse=True)

        if target:
            paths = [p for p in paths if p.target == target]

        return paths[:max_paths]

    async def delete_by_subject(self, subject: str) -> int:
        """Delete all edges from a subject, return count deleted"""
        result = await self._session.execute(
            delete(GraphEdge).where(GraphEdge.subject == subject)
        )
        return result.rowcount or 0

    async def list_all(self) -> list[GraphEdgeEntity]:
        """List all graph edges"""
        result = await self._session.execute(
            select(GraphEdge).order_by(GraphEdge.weight.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete_all(self) -> int:
        """Delete all edges, return count deleted"""
        result = await self._session.execute(delete(GraphEdge))
        return result.rowcount or 0

    async def update_weight(
        self, subject: str, predicate: str, obj: str, weight: float
    ) -> bool:
        """Update edge weight, return True if updated"""
        result = await self._session.execute(
            update(GraphEdge)
            .where(GraphEdge.subject == subject)
            .where(GraphEdge.predicate == predicate)
            .where(GraphEdge.object == obj)
            .values(weight=weight)
        )
        return (result.rowcount or 0) > 0

    async def count(self) -> int:
        """Count total edges"""
        result = await self._session.execute(select(func.count(GraphEdge.id)))
        return result.scalar() or 0
