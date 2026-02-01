"""
Integration tests to verify feature parity between PostgreSQL and SurrealDB backends.

These tests run against both backends to ensure consistent behavior.
Run with: pytest tests/integration/ -v
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from kiroku_memory.db.entities import (
    ResourceEntity,
    ItemEntity,
    CategoryEntity,
    GraphEdgeEntity,
    CategoryAccessEntity,
)


class TestResourceOperations:
    """Test resource CRUD operations across backends"""

    @pytest.mark.asyncio
    async def test_resource_lifecycle(self, unit_of_work, backend):
        """Test full resource lifecycle: create, read, list"""
        # Create
        resource = ResourceEntity(
            id=uuid4(),
            source=f"test-{backend}",
            content="Test content for integration test",
            metadata={"backend": backend},
        )
        resource_id = await unit_of_work.resources.create(resource)

        # Read
        retrieved = await unit_of_work.resources.get(resource_id)
        assert retrieved is not None
        assert retrieved.source == resource.source
        assert retrieved.content == resource.content

        # List
        resources = await unit_of_work.resources.list(limit=10)
        assert len(resources) >= 1


class TestItemOperations:
    """Test item CRUD operations across backends"""

    @pytest.mark.asyncio
    async def test_item_lifecycle(self, unit_of_work, backend):
        """Test full item lifecycle"""
        # Create resource first
        resource = ResourceEntity(
            id=uuid4(),
            source="test",
            content="Test",
        )
        await unit_of_work.resources.create(resource)

        # Create item
        item = ItemEntity(
            id=uuid4(),
            resource_id=resource.id,
            subject="test_subject",
            predicate="test_predicate",
            object="test_object",
            category="test_category",
            confidence=0.9,
        )
        item_id = await unit_of_work.items.create(item)

        # Read
        retrieved = await unit_of_work.items.get(item_id)
        assert retrieved is not None
        assert retrieved.subject == item.subject
        assert retrieved.status == "active"

        # Update status
        await unit_of_work.items.update_status(item_id, "archived")
        updated = await unit_of_work.items.get(item_id)
        assert updated.status == "archived"

    @pytest.mark.asyncio
    async def test_item_filtering(self, unit_of_work, backend):
        """Test item list filtering"""
        # Create items in different categories
        for cat in ["cat_a", "cat_a", "cat_b"]:
            item = ItemEntity(
                id=uuid4(),
                subject="test",
                predicate="is",
                object=cat,
                category=cat,
            )
            await unit_of_work.items.create(item)

        # Filter by category
        cat_a_items = await unit_of_work.items.list(category="cat_a")
        assert len(cat_a_items) == 2

        # Count
        total = await unit_of_work.items.count()
        assert total == 3

        count_a = await unit_of_work.items.count(category="cat_a")
        assert count_a == 2


class TestCategoryOperations:
    """Test category operations across backends"""

    @pytest.mark.asyncio
    async def test_category_upsert(self, unit_of_work, backend):
        """Test category upsert behavior"""
        category = CategoryEntity(
            id=uuid4(),
            name="test_category",
            summary="Initial summary",
        )

        # First upsert (create)
        cat_id = await unit_of_work.categories.upsert(category)

        # Second upsert (update)
        category.summary = "Updated summary"
        updated_id = await unit_of_work.categories.upsert(category)
        assert updated_id == cat_id

        # Verify update
        retrieved = await unit_of_work.categories.get_by_name("test_category")
        assert retrieved.summary == "Updated summary"


class TestGraphOperations:
    """Test graph operations across backends"""

    @pytest.mark.asyncio
    async def test_graph_traversal(self, unit_of_work, backend):
        """Test graph edge creation and traversal"""
        # Create edges: A -> B -> C
        edges = [
            GraphEdgeEntity(id=uuid4(), subject="A", predicate="connects", object="B", weight=1.0),
            GraphEdgeEntity(id=uuid4(), subject="B", predicate="connects", object="C", weight=0.8),
        ]
        for edge in edges:
            await unit_of_work.graph.create(edge)

        # Get direct connections from A
        from_a = await unit_of_work.graph.get_by_subject("A")
        assert len(from_a) == 1
        assert from_a[0].object == "B"

        # Get neighbors of B (should include both A and C connections)
        neighbors = await unit_of_work.graph.get_neighbors("B", depth=1)
        assert len(neighbors) == 2


class TestEmbeddingOperations:
    """Test embedding operations across backends"""

    @pytest.mark.asyncio
    async def test_embedding_search(self, unit_of_work, backend):
        """Test vector search functionality"""
        import random
        random.seed(42)

        # Create items with embeddings
        base_embedding = [random.random() for _ in range(1536)]

        items = []
        for i in range(3):
            item = ItemEntity(
                id=uuid4(),
                subject=f"item_{i}",
                predicate="has",
                object=f"value_{i}",
            )
            await unit_of_work.items.create(item)
            items.append(item)

            # Slightly different embeddings
            embedding = [v + (i * 0.1) for v in base_embedding]
            await unit_of_work.embeddings.upsert(item.id, embedding)

        # Search with base embedding
        results = await unit_of_work.embeddings.search(
            query_vector=base_embedding,
            limit=10,
            min_similarity=0.5,
        )

        # Should find items, with first being most similar
        assert len(results) >= 1
        assert results[0].item.subject == "item_0"  # Most similar to base


class TestCategoryAccessOperations:
    """Test category access tracking across backends"""

    @pytest.mark.asyncio
    async def test_access_tracking(self, unit_of_work, backend):
        """Test category access logging and counting"""
        # Log accesses
        categories = ["prefs", "prefs", "facts", "prefs"]
        for cat in categories:
            access = CategoryAccessEntity(
                id=uuid4(),
                category=cat,
            )
            await unit_of_work.category_accesses.create(access)

        # Count by category
        counts = await unit_of_work.category_accesses.count_by_category()
        assert counts.get("prefs", 0) == 3
        assert counts.get("facts", 0) == 1

    @pytest.mark.asyncio
    async def test_access_cleanup(self, unit_of_work, backend):
        """Test old access cleanup"""
        # Create old and new accesses
        old = CategoryAccessEntity(
            id=uuid4(),
            category="old",
            accessed_at=datetime.utcnow() - timedelta(days=30),
        )
        new = CategoryAccessEntity(
            id=uuid4(),
            category="new",
        )
        await unit_of_work.category_accesses.create(old)
        await unit_of_work.category_accesses.create(new)

        # Cleanup
        cutoff = datetime.utcnow() - timedelta(days=7)
        deleted = await unit_of_work.category_accesses.cleanup_old(cutoff)
        assert deleted == 1

        # Verify
        remaining = await unit_of_work.category_accesses.get_recent()
        assert len(remaining) == 1
        assert remaining[0].category == "new"
