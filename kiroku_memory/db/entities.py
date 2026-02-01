"""Domain entities - backend-agnostic data models"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class ResourceEntity:
    """Raw append-only log entry"""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    source: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ItemEntity:
    """Atomic fact extracted from resources"""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    resource_id: Optional[UUID] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    category: Optional[str] = None
    confidence: float = 1.0
    status: str = "active"
    supersedes: Optional[UUID] = None
    # Embedding (optional, for backends that store it inline)
    embedding: Optional[list[float]] = None


@dataclass
class CategoryEntity:
    """Category with evolving summary"""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    summary: Optional[str] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GraphEdgeEntity:
    """Knowledge graph edge"""
    id: UUID = field(default_factory=uuid4)
    subject: str = ""
    predicate: str = ""
    object: str = ""
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CategoryAccessEntity:
    """Category access log for priority scoring"""
    id: UUID = field(default_factory=uuid4)
    category: str = ""
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "context"


@dataclass
class EmbeddingSearchResult:
    """Result from embedding similarity search"""
    item: ItemEntity
    similarity: float
