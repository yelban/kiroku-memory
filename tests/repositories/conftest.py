"""Test fixtures for repository tests"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio

from kiroku_memory.db.entities import (
    ResourceEntity,
    ItemEntity,
    CategoryEntity,
    GraphEdgeEntity,
    CategoryAccessEntity,
)


# Test data fixtures
@pytest.fixture
def sample_resource() -> ResourceEntity:
    """Create a sample resource entity"""
    return ResourceEntity(
        id=uuid4(),
        source="test",
        content="User prefers dark mode and uses vim keybindings.",
        metadata={"test": True},
    )


@pytest.fixture
def sample_items(sample_resource: ResourceEntity) -> list[ItemEntity]:
    """Create sample item entities"""
    return [
        ItemEntity(
            id=uuid4(),
            resource_id=sample_resource.id,
            subject="user",
            predicate="prefers",
            object="dark mode",
            category="preferences",
            confidence=0.9,
        ),
        ItemEntity(
            id=uuid4(),
            resource_id=sample_resource.id,
            subject="user",
            predicate="uses",
            object="vim keybindings",
            category="preferences",
            confidence=0.85,
        ),
    ]


@pytest.fixture
def sample_category() -> CategoryEntity:
    """Create a sample category entity"""
    return CategoryEntity(
        id=uuid4(),
        name="preferences",
        summary="User preferences for UI and editing.",
    )


@pytest.fixture
def sample_graph_edges() -> list[GraphEdgeEntity]:
    """Create sample graph edge entities"""
    return [
        GraphEdgeEntity(
            id=uuid4(),
            subject="user",
            predicate="prefers",
            object="dark_mode",
            weight=0.9,
        ),
        GraphEdgeEntity(
            id=uuid4(),
            subject="dark_mode",
            predicate="is_a",
            object="ui_preference",
            weight=1.0,
        ),
    ]


@pytest.fixture
def sample_embedding() -> list[float]:
    """Create a sample embedding vector (1536 dimensions)"""
    import random
    random.seed(42)
    return [random.random() for _ in range(1536)]


@pytest.fixture
def sample_category_access() -> CategoryAccessEntity:
    """Create a sample category access entity"""
    return CategoryAccessEntity(
        id=uuid4(),
        category="preferences",
        source="context",
    )


# SurrealDB fixtures
@pytest_asyncio.fixture
async def surreal_client() -> AsyncGenerator:
    """Create a temporary SurrealDB client for testing"""
    # Skip if surrealdb not installed
    pytest.importorskip("surrealdb")

    from surrealdb import AsyncSurreal

    # Use temporary directory for test database
    with tempfile.TemporaryDirectory() as tmpdir:
        url = f"file://{tmpdir}/test"

        client = AsyncSurreal(url)
        await client.connect()
        await client.use("test", "test")

        # Initialize schema
        schema_path = Path(__file__).parent.parent.parent / "kiroku_memory" / "db" / "surrealdb" / "schema.surql"
        if schema_path.exists():
            schema_sql = schema_path.read_text()
            await client.query(schema_sql)

        yield client

        await client.close()


@pytest_asyncio.fixture
async def surreal_uow(surreal_client) -> AsyncGenerator:
    """Create a SurrealDB Unit of Work for testing"""
    from kiroku_memory.db.repositories.surrealdb import SurrealUnitOfWork

    uow = SurrealUnitOfWork(surreal_client)
    yield uow
