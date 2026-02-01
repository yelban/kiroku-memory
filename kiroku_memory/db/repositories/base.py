"""Abstract repository interfaces - backend agnostic"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from ..entities import (
    ResourceEntity,
    ItemEntity,
    CategoryEntity,
    GraphEdgeEntity,
    CategoryAccessEntity,
    EmbeddingSearchResult,
)


class ResourceRepository(ABC):
    """Repository for raw resource logs"""

    @abstractmethod
    async def create(self, entity: ResourceEntity) -> UUID:
        """Create a new resource, return its ID"""
        ...

    @abstractmethod
    async def get(self, resource_id: UUID) -> Optional[ResourceEntity]:
        """Get resource by ID"""
        ...

    @abstractmethod
    async def list(
        self,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[ResourceEntity]:
        """List resources with optional filters"""
        ...


class ItemRepository(ABC):
    """Repository for atomic fact items"""

    @abstractmethod
    async def create(self, entity: ItemEntity) -> UUID:
        """Create a single item, return its ID"""
        ...

    @abstractmethod
    async def create_many(self, entities: Sequence[ItemEntity]) -> list[UUID]:
        """Create multiple items, return their IDs"""
        ...

    @abstractmethod
    async def get(self, item_id: UUID) -> Optional[ItemEntity]:
        """Get item by ID"""
        ...

    @abstractmethod
    async def update(self, entity: ItemEntity) -> None:
        """Update an existing item"""
        ...

    @abstractmethod
    async def update_status(self, item_id: UUID, status: str) -> None:
        """Update item status (active, archived, deleted)"""
        ...

    @abstractmethod
    async def list(
        self,
        category: Optional[str] = None,
        status: str = "active",
        limit: int = 100,
    ) -> list[ItemEntity]:
        """List items with optional filters"""
        ...

    @abstractmethod
    async def list_by_resource(self, resource_id: UUID) -> list[ItemEntity]:
        """List all items from a specific resource"""
        ...

    @abstractmethod
    async def list_by_subject(self, subject: str, status: str = "active") -> list[ItemEntity]:
        """List items with matching subject"""
        ...

    @abstractmethod
    async def count(
        self,
        category: Optional[str] = None,
        status: str = "active",
    ) -> int:
        """Count items with optional filters"""
        ...

    @abstractmethod
    async def find_potential_conflicts(
        self,
        subject: str,
        predicate: str,
        exclude_id: Optional[UUID] = None,
    ) -> list[ItemEntity]:
        """Find items that may conflict with given subject/predicate"""
        ...


class CategoryRepository(ABC):
    """Repository for category summaries"""

    @abstractmethod
    async def create(self, entity: CategoryEntity) -> UUID:
        """Create a new category"""
        ...

    @abstractmethod
    async def get(self, category_id: UUID) -> Optional[CategoryEntity]:
        """Get category by ID"""
        ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[CategoryEntity]:
        """Get category by name"""
        ...

    @abstractmethod
    async def list(self) -> list[CategoryEntity]:
        """List all categories"""
        ...

    @abstractmethod
    async def update_summary(self, name: str, summary: str) -> None:
        """Update category summary"""
        ...

    @abstractmethod
    async def upsert(self, entity: CategoryEntity) -> UUID:
        """Create or update category by name"""
        ...


class GraphRepository(ABC):
    """Repository for knowledge graph edges"""

    @abstractmethod
    async def create(self, entity: GraphEdgeEntity) -> UUID:
        """Create a graph edge"""
        ...

    @abstractmethod
    async def create_many(self, entities: Sequence[GraphEdgeEntity]) -> list[UUID]:
        """Create multiple edges"""
        ...

    @abstractmethod
    async def get_by_subject(self, subject: str) -> list[GraphEdgeEntity]:
        """Get all edges from a subject"""
        ...

    @abstractmethod
    async def get_by_object(self, obj: str) -> list[GraphEdgeEntity]:
        """Get all edges to an object"""
        ...

    @abstractmethod
    async def get_neighbors(self, entity: str, depth: int = 1) -> list[GraphEdgeEntity]:
        """Get edges within N hops of an entity"""
        ...

    @abstractmethod
    async def delete_by_subject(self, subject: str) -> int:
        """Delete all edges from a subject, return count deleted"""
        ...


class EmbeddingRepository(ABC):
    """Repository for vector embeddings and similarity search"""

    @abstractmethod
    async def upsert(self, item_id: UUID, vector: list[float]) -> None:
        """Insert or update embedding for an item"""
        ...

    @abstractmethod
    async def get(self, item_id: UUID) -> Optional[list[float]]:
        """Get embedding vector for an item"""
        ...

    @abstractmethod
    async def delete(self, item_id: UUID) -> None:
        """Delete embedding for an item"""
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        min_similarity: float = 0.5,
        status_filter: str = "active",
    ) -> list[EmbeddingSearchResult]:
        """Search for similar items by vector"""
        ...

    @abstractmethod
    async def batch_upsert(self, embeddings: dict[UUID, list[float]]) -> int:
        """Batch insert/update embeddings, return count"""
        ...


class CategoryAccessRepository(ABC):
    """Repository for category access tracking"""

    @abstractmethod
    async def create(self, entity: CategoryAccessEntity) -> UUID:
        """Log a category access"""
        ...

    @abstractmethod
    async def get_recent(
        self,
        category: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[CategoryAccessEntity]:
        """Get recent accesses"""
        ...

    @abstractmethod
    async def count_by_category(
        self,
        since: Optional[datetime] = None,
    ) -> dict[str, int]:
        """Count accesses per category"""
        ...

    @abstractmethod
    async def cleanup_old(self, before: datetime) -> int:
        """Delete old access records, return count deleted"""
        ...


class UnitOfWork(ABC):
    """Unit of work pattern for transaction management"""

    resources: ResourceRepository
    items: ItemRepository
    categories: CategoryRepository
    graph: GraphRepository
    embeddings: EmbeddingRepository
    category_accesses: CategoryAccessRepository

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction"""
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction"""
        ...
