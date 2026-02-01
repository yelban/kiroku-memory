"""Tests for SurrealDB repository implementations"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from kiroku_memory.db.entities import (
    ResourceEntity,
    ItemEntity,
    CategoryEntity,
    GraphEdgeEntity,
    CategoryAccessEntity,
)


# Skip all tests if surrealdb not installed
pytestmark = pytest.mark.skipif(
    not pytest.importorskip("surrealdb", reason="surrealdb not installed"),
    reason="surrealdb not installed",
)


class TestSurrealResourceRepository:
    """Tests for SurrealResourceRepository"""

    @pytest.mark.asyncio
    async def test_create_and_get(self, surreal_uow, sample_resource):
        """Test creating and retrieving a resource"""
        # Create
        resource_id = await surreal_uow.resources.create(sample_resource)
        assert resource_id == sample_resource.id

        # Get
        retrieved = await surreal_uow.resources.get(resource_id)
        assert retrieved is not None
        assert retrieved.id == sample_resource.id
        assert retrieved.source == sample_resource.source
        assert retrieved.content == sample_resource.content

    @pytest.mark.asyncio
    async def test_list_resources(self, surreal_uow):
        """Test listing resources with filters"""
        # Create multiple resources
        for i in range(3):
            entity = ResourceEntity(
                id=uuid4(),
                source=f"source_{i % 2}",
                content=f"Content {i}",
            )
            await surreal_uow.resources.create(entity)

        # List all
        all_resources = await surreal_uow.resources.list(limit=10)
        assert len(all_resources) == 3

        # List by source
        filtered = await surreal_uow.resources.list(source="source_0", limit=10)
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, surreal_uow):
        """Test getting a nonexistent resource"""
        result = await surreal_uow.resources.get(uuid4())
        assert result is None


class TestSurrealItemRepository:
    """Tests for SurrealItemRepository"""

    @pytest.mark.asyncio
    async def test_create_and_get(self, surreal_uow, sample_resource, sample_items):
        """Test creating and retrieving items"""
        # First create the resource
        await surreal_uow.resources.create(sample_resource)

        # Create items
        for item in sample_items:
            item_id = await surreal_uow.items.create(item)
            assert item_id == item.id

        # Get item
        retrieved = await surreal_uow.items.get(sample_items[0].id)
        assert retrieved is not None
        assert retrieved.subject == sample_items[0].subject
        assert retrieved.predicate == sample_items[0].predicate

    @pytest.mark.asyncio
    async def test_update_status(self, surreal_uow, sample_items):
        """Test updating item status"""
        item = sample_items[0]
        await surreal_uow.items.create(item)

        # Update status
        await surreal_uow.items.update_status(item.id, "archived")

        # Verify
        retrieved = await surreal_uow.items.get(item.id)
        assert retrieved.status == "archived"

    @pytest.mark.asyncio
    async def test_list_by_category(self, surreal_uow, sample_items):
        """Test listing items by category"""
        for item in sample_items:
            await surreal_uow.items.create(item)

        # List by category
        items = await surreal_uow.items.list(category="preferences")
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_count(self, surreal_uow, sample_items):
        """Test counting items"""
        for item in sample_items:
            await surreal_uow.items.create(item)

        count = await surreal_uow.items.count()
        assert count == 2

        count_by_category = await surreal_uow.items.count(category="preferences")
        assert count_by_category == 2


class TestSurrealCategoryRepository:
    """Tests for SurrealCategoryRepository"""

    @pytest.mark.asyncio
    async def test_create_and_get(self, surreal_uow, sample_category):
        """Test creating and retrieving a category"""
        cat_id = await surreal_uow.categories.create(sample_category)
        assert cat_id == sample_category.id

        retrieved = await surreal_uow.categories.get(cat_id)
        assert retrieved is not None
        assert retrieved.name == sample_category.name

    @pytest.mark.asyncio
    async def test_get_by_name(self, surreal_uow, sample_category):
        """Test getting category by name"""
        await surreal_uow.categories.create(sample_category)

        retrieved = await surreal_uow.categories.get_by_name("preferences")
        assert retrieved is not None
        assert retrieved.id == sample_category.id

    @pytest.mark.asyncio
    async def test_upsert(self, surreal_uow, sample_category):
        """Test upserting a category"""
        # First create
        cat_id = await surreal_uow.categories.upsert(sample_category)
        assert cat_id == sample_category.id

        # Update via upsert
        sample_category.summary = "Updated summary"
        updated_id = await surreal_uow.categories.upsert(sample_category)
        assert updated_id == cat_id

        # Verify
        retrieved = await surreal_uow.categories.get_by_name("preferences")
        assert retrieved.summary == "Updated summary"


class TestSurrealGraphRepository:
    """Tests for SurrealGraphRepository"""

    @pytest.mark.asyncio
    async def test_create_and_get_by_subject(self, surreal_uow, sample_graph_edges):
        """Test creating and retrieving graph edges"""
        for edge in sample_graph_edges:
            await surreal_uow.graph.create(edge)

        # Get by subject
        edges = await surreal_uow.graph.get_by_subject("user")
        assert len(edges) == 1
        assert edges[0].predicate == "prefers"

    @pytest.mark.asyncio
    async def test_get_neighbors(self, surreal_uow, sample_graph_edges):
        """Test getting neighbors"""
        for edge in sample_graph_edges:
            await surreal_uow.graph.create(edge)

        # Get neighbors of dark_mode
        neighbors = await surreal_uow.graph.get_neighbors("dark_mode", depth=1)
        assert len(neighbors) == 2  # Connected to both user and ui_preference

    @pytest.mark.asyncio
    async def test_delete_by_subject(self, surreal_uow, sample_graph_edges):
        """Test deleting edges by subject"""
        for edge in sample_graph_edges:
            await surreal_uow.graph.create(edge)

        # Delete edges from "user"
        deleted = await surreal_uow.graph.delete_by_subject("user")
        assert deleted == 1

        # Verify
        edges = await surreal_uow.graph.get_by_subject("user")
        assert len(edges) == 0


class TestSurrealEmbeddingRepository:
    """Tests for SurrealEmbeddingRepository"""

    @pytest.mark.asyncio
    async def test_upsert_and_get(self, surreal_uow, sample_items, sample_embedding):
        """Test upserting and retrieving embeddings"""
        item = sample_items[0]
        await surreal_uow.items.create(item)

        # Upsert embedding
        await surreal_uow.embeddings.upsert(item.id, sample_embedding)

        # Get embedding
        retrieved = await surreal_uow.embeddings.get(item.id)
        assert retrieved is not None
        assert len(retrieved) == 1536
        assert retrieved[:10] == sample_embedding[:10]  # Compare first 10 values

    @pytest.mark.asyncio
    async def test_search(self, surreal_uow, sample_items, sample_embedding):
        """Test vector search"""
        # Create items with embeddings
        for i, item in enumerate(sample_items):
            await surreal_uow.items.create(item)
            # Slightly modify embedding for each item
            modified_embedding = [v + (i * 0.01) for v in sample_embedding]
            await surreal_uow.embeddings.upsert(item.id, modified_embedding)

        # Search
        results = await surreal_uow.embeddings.search(
            query_vector=sample_embedding,
            limit=10,
            min_similarity=0.5,
        )

        # Should find both items
        assert len(results) >= 1
        # First result should be most similar
        assert results[0].similarity > 0.9

    @pytest.mark.asyncio
    async def test_delete(self, surreal_uow, sample_items, sample_embedding):
        """Test deleting embeddings"""
        item = sample_items[0]
        await surreal_uow.items.create(item)
        await surreal_uow.embeddings.upsert(item.id, sample_embedding)

        # Delete
        await surreal_uow.embeddings.delete(item.id)

        # Verify
        retrieved = await surreal_uow.embeddings.get(item.id)
        assert retrieved is None


class TestSurrealCategoryAccessRepository:
    """Tests for SurrealCategoryAccessRepository"""

    @pytest.mark.asyncio
    async def test_create_and_get_recent(self, surreal_uow, sample_category_access):
        """Test creating and retrieving category accesses"""
        await surreal_uow.category_accesses.create(sample_category_access)

        # Get recent
        accesses = await surreal_uow.category_accesses.get_recent(limit=10)
        assert len(accesses) == 1
        assert accesses[0].category == "preferences"

    @pytest.mark.asyncio
    async def test_count_by_category(self, surreal_uow):
        """Test counting accesses by category"""
        # Create multiple accesses
        for cat in ["preferences", "preferences", "facts"]:
            entity = CategoryAccessEntity(
                id=uuid4(),
                category=cat,
            )
            await surreal_uow.category_accesses.create(entity)

        # Count
        counts = await surreal_uow.category_accesses.count_by_category()
        assert counts.get("preferences", 0) == 2
        assert counts.get("facts", 0) == 1

    @pytest.mark.asyncio
    async def test_cleanup_old(self, surreal_uow):
        """Test cleaning up old accesses"""
        # Create old and new accesses
        old_access = CategoryAccessEntity(
            id=uuid4(),
            category="old",
            accessed_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30),
        )
        new_access = CategoryAccessEntity(
            id=uuid4(),
            category="new",
        )
        await surreal_uow.category_accesses.create(old_access)
        await surreal_uow.category_accesses.create(new_access)

        # Cleanup old (older than 7 days)
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        deleted = await surreal_uow.category_accesses.cleanup_old(cutoff)
        assert deleted == 1

        # Verify
        accesses = await surreal_uow.category_accesses.get_recent(limit=10)
        assert len(accesses) == 1
        assert accesses[0].category == "new"
