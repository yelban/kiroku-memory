"""Domain entities - backend-agnostic data models"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    """Return current UTC time as naive datetime (for DB compatibility)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class ResourceEntity:
    """Raw append-only log entry"""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    source: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ItemEntity:
    """Atomic fact extracted from resources"""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    resource_id: Optional[UUID] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    category: Optional[str] = None
    confidence: float = 1.0
    status: str = "active"
    supersedes: Optional[UUID] = None
    # Canonical forms for entity resolution (matching/dedup)
    canonical_subject: Optional[str] = None
    canonical_object: Optional[str] = None
    # Reified statements: if not None, this item is a meta-fact about the referenced item
    meta_about: Optional[UUID] = None
    # Embedding (optional, for backends that store it inline)
    embedding: Optional[list[float]] = None


@dataclass
class CategoryEntity:
    """Category with evolving summary"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    summary: Optional[str] = None
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class GraphEdgeEntity:
    """Knowledge graph edge"""
    id: UUID = field(default_factory=uuid4)
    subject: str = ""
    predicate: str = ""
    object: str = ""
    weight: float = 1.0
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class GraphPath:
    """A path through the knowledge graph"""
    source: str
    target: str
    edges: list[GraphEdgeEntity]
    hops: list[str]
    distance: int
    weight: float


@dataclass
class CategoryAccessEntity:
    """Category access log for priority scoring"""
    id: UUID = field(default_factory=uuid4)
    category: str = ""
    accessed_at: datetime = field(default_factory=_utcnow)
    source: str = "context"


@dataclass
class EmbeddingSearchResult:
    """Result from embedding similarity search"""
    item: ItemEntity
    similarity: float
