"""SQLAlchemy models for AI Agent Memory System"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Resource(Base):
    """Raw append-only logs for provenance"""
    __tablename__ = "resources"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Relationships
    items: Mapped[list["Item"]] = relationship("Item", back_populates="resource")

    __table_args__ = (
        Index("idx_resources_created_at", created_at.desc()),
        Index("idx_resources_source", source),
    )


class Item(Base):
    """Atomic facts extracted from resources"""
    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    resource_id: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("resources.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    predicate: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    object: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    supersedes: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    canonical_subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    canonical_object: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_about: Mapped[Optional[UUID]] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    resource: Mapped[Optional["Resource"]] = relationship("Resource", back_populates="items")
    embedding: Mapped[Optional["Embedding"]] = relationship("Embedding", back_populates="item", uselist=False)
    superseded_item: Mapped[Optional["Item"]] = relationship(
        "Item", remote_side=[id], foreign_keys=[supersedes]
    )
    meta_facts: Mapped[list["Item"]] = relationship(
        "Item", foreign_keys=[meta_about], cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived', 'deleted')", name="check_item_status"),
        Index("idx_items_created_at", created_at.desc()),
        Index("idx_items_category", category),
        Index("idx_items_status", status),
        Index("idx_items_subject", subject),
        Index("idx_items_resource_id", resource_id),
        Index("idx_items_canonical_subject", canonical_subject),
        Index("idx_items_canonical_object", canonical_object),
        Index("idx_items_meta_about", meta_about),
    )


class Category(Base):
    """Evolving category summaries"""
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_categories_name", name),
    )


class GraphEdge(Base):
    """Knowledge graph relationships"""
    __tablename__ = "graph_edges"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    predicate: Mapped[str] = mapped_column(Text, nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_graph_edges_subject", subject),
        Index("idx_graph_edges_object", object),
        Index("idx_graph_edges_predicate", predicate),
    )


class Embedding(Base):
    """Vector embeddings for semantic search"""
    __tablename__ = "embeddings"

    item_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    embedding = Column(Vector(1536))

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="embedding")


class CategoryAccess(Base):
    """Track category access for dynamic priority scoring"""
    __tablename__ = "category_accesses"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(Text, default="context")  # e.g., "context", "recall", "api"

    __table_args__ = (
        Index("idx_category_accesses_category", category),
        Index("idx_category_accesses_accessed_at", accessed_at.desc()),
    )
