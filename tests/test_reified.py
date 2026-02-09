"""Tests for P2-7: Reified Statements (meta-facts)"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from kiroku_memory.db.entities import ItemEntity


@pytest_asyncio.fixture
async def surreal_uow():
    """Create SurrealDB UoW with schema initialized"""
    pytest.importorskip("surrealdb")

    from surrealdb import AsyncSurreal
    from kiroku_memory.db.repositories.surrealdb import SurrealUnitOfWork

    with tempfile.TemporaryDirectory() as tmpdir:
        url = f"file://{tmpdir}/test"
        client = AsyncSurreal(url)
        await client.connect()
        await client.use("test", "test")

        schema_path = (
            Path(__file__).parent.parent
            / "kiroku_memory"
            / "db"
            / "surrealdb"
            / "schema.surql"
        )
        if schema_path.exists():
            schema_sql = schema_path.read_text()
            await client.query(schema_sql)

        uow = SurrealUnitOfWork(client)
        yield uow

        await client.close()


@pytest_asyncio.fixture
async def surreal_uow_with_item(surreal_uow):
    """Create a normal item in the DB and return (uow, item_id)"""
    from kiroku_memory.entity_resolution import resolve_entity

    item = ItemEntity(
        id=uuid4(),
        subject="Alice",
        predicate="likes",
        object="Python",
        category="preferences",
        confidence=0.9,
        canonical_subject=resolve_entity("Alice"),
        canonical_object=resolve_entity("Python"),
    )
    item_id = await surreal_uow.items.create(item)
    return surreal_uow, item_id, item


# ============ Repository Tests ============


@pytest.mark.asyncio
async def test_create_meta_fact(surreal_uow_with_item):
    """Create a meta-fact and verify its meta_about field"""
    uow, item_id, _ = surreal_uow_with_item

    meta_id = await uow.items.create_meta_fact(
        about_item_id=item_id,
        predicate="has_source",
        object_value="conversation-2024-01",
    )

    meta = await uow.items.get(meta_id)
    assert meta is not None
    assert meta.meta_about == item_id
    assert meta.predicate == "has_source"
    assert meta.object == "conversation-2024-01"
    assert meta.category == "meta"
    assert meta.subject is None


@pytest.mark.asyncio
async def test_get_meta_facts(surreal_uow_with_item):
    """Get all meta-facts for an item"""
    uow, item_id, _ = surreal_uow_with_item

    await uow.items.create_meta_fact(
        about_item_id=item_id,
        predicate="has_source",
        object_value="conv-01",
    )
    await uow.items.create_meta_fact(
        about_item_id=item_id,
        predicate="verified_by",
        object_value="user",
    )

    meta_facts = await uow.items.get_meta_facts(item_id)
    assert len(meta_facts) == 2
    predicates = {m.predicate for m in meta_facts}
    assert predicates == {"has_source", "verified_by"}
    for m in meta_facts:
        assert m.meta_about == item_id


@pytest.mark.asyncio
async def test_list_excludes_meta(surreal_uow_with_item):
    """list() should not return meta-facts"""
    uow, item_id, _ = surreal_uow_with_item

    await uow.items.create_meta_fact(
        about_item_id=item_id,
        predicate="extraction_method",
        object_value="gpt-4o-mini",
    )

    items = await uow.items.list(status="active")
    assert len(items) == 1
    assert items[0].id == item_id
    assert items[0].meta_about is None


@pytest.mark.asyncio
async def test_list_by_subject_excludes_meta(surreal_uow_with_item):
    """list_by_subject() should not return meta-facts"""
    uow, item_id, _ = surreal_uow_with_item

    await uow.items.create_meta_fact(
        about_item_id=item_id,
        predicate="has_source",
        object_value="test",
    )

    items = await uow.items.list_by_subject("Alice")
    assert len(items) == 1
    assert items[0].id == item_id


@pytest.mark.asyncio
async def test_list_distinct_categories_excludes_meta(surreal_uow_with_item):
    """list_distinct_categories() should not include 'meta' category"""
    uow, item_id, _ = surreal_uow_with_item

    await uow.items.create_meta_fact(
        about_item_id=item_id,
        predicate="extraction_method",
        object_value="gpt-4o-mini",
    )

    categories = await uow.items.list_distinct_categories()
    assert "meta" not in categories
    assert "preferences" in categories


# ============ API Tests ============


@pytest.mark.asyncio
async def test_api_get_meta():
    """GET /v2/items/{id}/meta endpoint"""
    from httpx import AsyncClient, ASGITransport

    import os
    os.environ.setdefault("BACKEND", "surrealdb")
    os.environ.setdefault("SURREAL_URL", "memory")

    from kiroku_memory.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create an item
        resp = await client.post("/v2/items", json={
            "subject": "Bob",
            "predicate": "likes",
            "object": "Rust",
            "category": "preferences",
        })
        assert resp.status_code == 200
        item_id = resp.json()["id"]

        # Add meta-fact
        resp = await client.post(f"/v2/items/{item_id}/meta", json={
            "predicate": "has_source",
            "object": "test-conv",
        })
        assert resp.status_code == 200
        meta = resp.json()
        assert meta["predicate"] == "has_source"
        assert meta["object"] == "test-conv"
        assert meta["meta_about"] == item_id

        # Get meta-facts
        resp = await client.get(f"/v2/items/{item_id}/meta")
        assert resp.status_code == 200
        meta_list = resp.json()
        assert len(meta_list) >= 1
        assert any(m["predicate"] == "has_source" for m in meta_list)


@pytest.mark.asyncio
async def test_api_post_meta_404():
    """POST /v2/items/{id}/meta should 404 for non-existent item"""
    from httpx import AsyncClient, ASGITransport

    import os
    os.environ.setdefault("BACKEND", "surrealdb")
    os.environ.setdefault("SURREAL_URL", "memory")

    from kiroku_memory.api import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_id = str(uuid4())
        resp = await client.post(f"/v2/items/{fake_id}/meta", json={
            "predicate": "has_source",
            "object": "test",
        })
        assert resp.status_code == 404
