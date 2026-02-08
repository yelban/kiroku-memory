"""Tests for P1: Entity Resolution (dual-field canonical approach)"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from kiroku_memory.entity_resolution import (
    normalize_entity,
    resolve_entity,
    BUILTIN_ALIASES,
)
from kiroku_memory.db.entities import ItemEntity, GraphEdgeEntity


# ============ Unit Tests: normalize_entity ============


class TestNormalizeEntity:
    def test_lowercase(self):
        assert normalize_entity("Python") == "python"

    def test_strip(self):
        assert normalize_entity("  user  ") == "user"

    def test_collapse_whitespace(self):
        assert normalize_entity("dark   mode") == "dark mode"

    def test_combined(self):
        assert normalize_entity("  Hello   World  ") == "hello world"

    def test_empty(self):
        assert normalize_entity("") == ""


# ============ Unit Tests: resolve_entity ============


class TestResolveEntity:
    def test_self_reference_chinese(self):
        assert resolve_entity("我") == "user"

    def test_self_reference_english(self):
        assert resolve_entity("I") == "user"
        assert resolve_entity("me") == "user"
        assert resolve_entity("myself") == "user"

    def test_self_reference_chinese_variants(self):
        assert resolve_entity("使用者") == "user"
        assert resolve_entity("用戶") == "user"
        assert resolve_entity("本人") == "user"

    def test_programming_languages(self):
        assert resolve_entity("js") == "javascript"
        assert resolve_entity("JS") == "javascript"
        assert resolve_entity("ts") == "typescript"
        assert resolve_entity("py") == "python"

    def test_tools(self):
        assert resolve_entity("pg") == "postgresql"
        assert resolve_entity("Postgres") == "postgresql"
        assert resolve_entity("k8s") == "kubernetes"

    def test_os(self):
        assert resolve_entity("mac") == "macos"
        assert resolve_entity("OSX") == "macos"

    def test_no_alias_passthrough(self):
        assert resolve_entity("FastAPI") == "fastapi"
        assert resolve_entity("Alice") == "alice"

    def test_normalize_before_alias(self):
        # Whitespace + case should still match alias
        assert resolve_entity("  Me  ") == "user"
        assert resolve_entity("  JS  ") == "javascript"


# ============ Unit Tests: BUILTIN_ALIASES ============


class TestBuiltinAliases:
    def test_all_keys_are_normalized(self):
        """All alias keys should already be in normalized form"""
        for key in BUILTIN_ALIASES:
            assert key == normalize_entity(key), f"Key '{key}' is not normalized"

    def test_all_values_are_normalized(self):
        """All alias values should be in normalized form"""
        for key, value in BUILTIN_ALIASES.items():
            assert value == normalize_entity(value), f"Value '{value}' for key '{key}' is not normalized"


# ============ Integration Tests (SurrealDB) ============


@pytest_asyncio.fixture
async def surreal_uow():
    """Create SurrealDB UoW with schema applied"""
    pytest.importorskip("surrealdb")

    from surrealdb import AsyncSurreal
    from kiroku_memory.db.repositories.surrealdb import SurrealUnitOfWork

    with tempfile.TemporaryDirectory() as tmpdir:
        url = f"file://{tmpdir}/test"
        client = AsyncSurreal(url)
        await client.connect()
        await client.use("test", "test")

        schema_path = Path(__file__).parent.parent / "kiroku_memory" / "db" / "surrealdb" / "schema.surql"
        if schema_path.exists():
            schema_sql = schema_path.read_text()
            await client.query(schema_sql)

        uow = SurrealUnitOfWork(client)
        yield uow
        await client.close()


@pytest.mark.asyncio
async def test_canonical_fields_on_create(surreal_uow):
    """Creating an item with canonical fields should persist them"""
    item = ItemEntity(
        id=uuid4(),
        subject="我",
        predicate="prefers",
        object="Dark Mode",
        category="preferences",
        canonical_subject=resolve_entity("我"),
        canonical_object=resolve_entity("Dark Mode"),
    )
    item_id = await surreal_uow.items.create(item)

    fetched = await surreal_uow.items.get(item_id)
    assert fetched is not None
    assert fetched.subject == "我"  # original preserved
    assert fetched.canonical_subject == "user"  # resolved
    assert fetched.object == "Dark Mode"  # original preserved
    assert fetched.canonical_object == "dark mode"  # resolved (no alias, just normalized)


@pytest.mark.asyncio
async def test_list_by_subject_uses_canonical(surreal_uow):
    """list_by_subject("我") should find items with subject="user" via canonical"""
    # Create item with subject="user"
    item1 = ItemEntity(
        id=uuid4(),
        subject="user",
        predicate="prefers",
        object="vim",
        category="preferences",
        canonical_subject=resolve_entity("user"),
        canonical_object=resolve_entity("vim"),
    )
    await surreal_uow.items.create(item1)

    # Create item with subject="我"
    item2 = ItemEntity(
        id=uuid4(),
        subject="我",
        predicate="likes",
        object="Python",
        category="preferences",
        canonical_subject=resolve_entity("我"),
        canonical_object=resolve_entity("Python"),
    )
    await surreal_uow.items.create(item2)

    # Query with "我" should find both (both canonical_subject="user")
    results = await surreal_uow.items.list_by_subject("我")
    assert len(results) == 2

    # Query with "user" should also find both
    results = await surreal_uow.items.list_by_subject("user")
    assert len(results) == 2

    # Query with "使用者" should also find both
    results = await surreal_uow.items.list_by_subject("使用者")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_find_conflicts_uses_canonical(surreal_uow):
    """find_potential_conflicts should match across aliases"""
    item = ItemEntity(
        id=uuid4(),
        subject="user",
        predicate="prefers",
        object="dark mode",
        category="preferences",
        canonical_subject=resolve_entity("user"),
        canonical_object=resolve_entity("dark mode"),
    )
    item_id = await surreal_uow.items.create(item)

    # Search conflicts for "我" + "prefers" should find the "user" item
    conflicts = await surreal_uow.items.find_potential_conflicts("我", "prefers")
    assert len(conflicts) >= 1
    assert any(c.id == item_id for c in conflicts)


@pytest.mark.asyncio
async def test_list_duplicates_uses_canonical(surreal_uow):
    """list_duplicates should detect dupes across aliases"""
    item1 = ItemEntity(
        id=uuid4(),
        subject="user",
        predicate="prefers",
        object="dark mode",
        category="preferences",
        canonical_subject=resolve_entity("user"),
        canonical_object=resolve_entity("dark mode"),
    )
    await surreal_uow.items.create(item1)

    item2 = ItemEntity(
        id=uuid4(),
        subject="我",
        predicate="prefers",
        object="Dark Mode",
        category="preferences",
        canonical_subject=resolve_entity("我"),
        canonical_object=resolve_entity("Dark Mode"),
    )
    await surreal_uow.items.create(item2)

    dupes = await surreal_uow.items.list_duplicates()
    assert len(dupes) >= 1
    # Both items should be in the same duplicate pair
    pair_ids = {dupes[0][0].id, dupes[0][1].id}
    assert item1.id in pair_ids
    assert item2.id in pair_ids


@pytest.mark.asyncio
async def test_graph_edges_use_canonical(surreal_uow):
    """Graph edges should be stored with canonical entity names"""
    # Simulate what api.py does: resolve before creating edge
    edge = GraphEdgeEntity(
        subject=resolve_entity("我"),
        predicate="prefers",
        object=resolve_entity("JS"),
    )
    await surreal_uow.graph.create(edge)

    # Query with canonical form
    edges = await surreal_uow.graph.get_neighbors("user", depth=1)
    assert len(edges) >= 1
    assert any(e.subject == "user" and e.object == "javascript" for e in edges)


@pytest.mark.asyncio
async def test_entity_lookup_with_alias(surreal_uow):
    """Entity lookup search should resolve aliases before querying"""
    from kiroku_memory.search import smart_search

    # Create items with subject="user"
    item = ItemEntity(
        id=uuid4(),
        subject="user",
        predicate="likes",
        object="Python",
        category="preferences",
        canonical_subject=resolve_entity("user"),
        canonical_object=resolve_entity("Python"),
    )
    await surreal_uow.items.create(item)

    # Create graph edge
    edge = GraphEdgeEntity(
        subject=resolve_entity("user"),
        predicate="likes",
        object=resolve_entity("Python"),
    )
    await surreal_uow.graph.create(edge)

    # Search "about 我" should find the item (resolves "我" → "user")
    result = await smart_search("about 我", surreal_uow)
    assert result["intent"] == "EntityLookup"
    assert len(result["items"]) >= 1
    assert any(r["subject"] == "user" for r in result["items"])


@pytest.mark.asyncio
async def test_context_graph_uses_canonical(surreal_uow):
    """get_tiered_context graph queries should use canonical subjects"""
    from kiroku_memory.summarize import get_tiered_context

    # Create items with subject="我" (canonical_subject="user")
    item = ItemEntity(
        id=uuid4(),
        subject="我",
        predicate="prefers",
        object="dark mode",
        category="preferences",
        canonical_subject=resolve_entity("我"),
        canonical_object=resolve_entity("dark mode"),
    )
    await surreal_uow.items.create(item)

    # Create graph edge with canonical forms
    edge = GraphEdgeEntity(
        subject="user",
        predicate="works_at",
        object="acme corp",
    )
    await surreal_uow.graph.create(edge)

    context = await get_tiered_context(
        surreal_uow,
        max_items_per_category=10,
        record_access=False,
    )

    # The item shows subject="我" in display
    assert "我 prefers dark mode" in context
    # The graph edge (user works_at acme corp) should appear as Related
    # because resolve_entity("我") = "user" matches the graph edge subject
    assert "works_at" in context
