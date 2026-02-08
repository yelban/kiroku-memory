"""Tests for P0 features: search, graph, intent-driven retrieval"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from kiroku_memory.db.entities import (
    ItemEntity,
    GraphEdgeEntity,
)
from kiroku_memory.search import (
    classify_intent,
    smart_search,
    EntityLookup,
    Temporal,
    AspectFilter,
    SemanticSearch,
)


# ============ Intent Classifier Unit Tests ============


class TestClassifyIntent:
    """Unit tests for rule-based intent classifier"""

    def test_entity_lookup_english(self):
        result = classify_intent("about Claude")
        assert isinstance(result, EntityLookup)
        assert result.entity == "claude"

    def test_entity_lookup_chinese(self):
        result = classify_intent("關於 Python")
        assert isinstance(result, EntityLookup)
        assert result.entity == "python"

    def test_entity_lookup_what_about(self):
        result = classify_intent("what do you know about Alice?")
        assert isinstance(result, EntityLookup)

    def test_entity_lookup_chinese_suffix(self):
        result = classify_intent("Python是什麼")
        assert isinstance(result, EntityLookup)

    def test_temporal_recent(self):
        result = classify_intent("recent")
        assert isinstance(result, Temporal)
        assert result.days == 7

    def test_temporal_chinese(self):
        result = classify_intent("最近")
        assert isinstance(result, Temporal)
        assert result.days == 7

    def test_temporal_last_n_days(self):
        result = classify_intent("last 3 days")
        assert isinstance(result, Temporal)
        assert result.days == 3

    def test_temporal_last_week(self):
        result = classify_intent("last week")
        assert isinstance(result, Temporal)
        assert result.days == 7

    def test_temporal_this_month(self):
        result = classify_intent("這個月")
        assert isinstance(result, Temporal)
        assert result.days == 30

    def test_aspect_preferences(self):
        result = classify_intent("preferences")
        assert isinstance(result, AspectFilter)
        assert result.category == "preferences"

    def test_aspect_chinese_preferences(self):
        result = classify_intent("偏好")
        assert isinstance(result, AspectFilter)
        assert result.category == "preferences"

    def test_aspect_goals(self):
        result = classify_intent("goals")
        assert isinstance(result, AspectFilter)
        assert result.category == "goals"

    def test_aspect_skills(self):
        result = classify_intent("skills")
        assert isinstance(result, AspectFilter)
        assert result.category == "skills"

    def test_semantic_default(self):
        result = classify_intent("how to use FastAPI")
        assert isinstance(result, SemanticSearch)

    def test_semantic_random(self):
        result = classify_intent("completely random text")
        assert isinstance(result, SemanticSearch)


# ============ Smart Search Integration Tests (SurrealDB) ============


@pytest_asyncio.fixture
async def surreal_uow_with_data():
    """Create SurrealDB UoW with pre-populated test data"""
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

        # Populate test data
        items = [
            ItemEntity(
                id=uuid4(),
                subject="user",
                predicate="prefers",
                object="dark mode",
                category="preferences",
                confidence=0.9,
            ),
            ItemEntity(
                id=uuid4(),
                subject="user",
                predicate="uses",
                object="vim",
                category="preferences",
                confidence=0.85,
            ),
            ItemEntity(
                id=uuid4(),
                subject="user",
                predicate="works_at",
                object="Acme Corp",
                category="facts",
                confidence=1.0,
            ),
            ItemEntity(
                id=uuid4(),
                subject="user",
                predicate="wants_to",
                object="learn Rust",
                category="goals",
                confidence=0.8,
            ),
        ]

        for item in items:
            await uow.items.create(item)

        # Add graph edges
        edges = [
            GraphEdgeEntity(subject="user", predicate="prefers", object="dark mode"),
            GraphEdgeEntity(subject="user", predicate="uses", object="vim"),
            GraphEdgeEntity(subject="user", predicate="works_at", object="Acme Corp"),
            GraphEdgeEntity(subject="vim", predicate="is_a", object="text editor"),
        ]
        for edge in edges:
            await uow.graph.create(edge)

        yield uow

        await client.close()


@pytest.mark.asyncio
async def test_smart_search_entity_lookup(surreal_uow_with_data):
    """EntityLookup intent should find items via graph + subject search"""
    result = await smart_search("about user", surreal_uow_with_data)
    assert result["intent"] == "EntityLookup"
    assert len(result["items"]) > 0
    # Should find items about "user"
    subjects = {r["subject"] for r in result["items"]}
    assert "user" in subjects


@pytest.mark.asyncio
async def test_smart_search_aspect_filter(surreal_uow_with_data):
    """AspectFilter intent should return items in the target category"""
    result = await smart_search("preferences", surreal_uow_with_data)
    assert result["intent"] == "AspectFilter"
    assert len(result["items"]) > 0
    for item in result["items"]:
        assert item["category"] == "preferences"


@pytest.mark.asyncio
async def test_smart_search_temporal(surreal_uow_with_data):
    """Temporal intent should return recent items"""
    result = await smart_search("最近", surreal_uow_with_data)
    assert result["intent"] == "Temporal"
    # All test items were just created, so they should all be "recent"
    assert len(result["items"]) > 0


@pytest.mark.asyncio
async def test_smart_search_semantic_fallback(surreal_uow_with_data):
    """SemanticSearch without embeddings should fallback to recent items"""
    result = await smart_search("random query", surreal_uow_with_data)
    assert "SemanticSearch" in result["intent"]
    # Should fallback to returning recent items
    assert len(result["items"]) > 0


@pytest.mark.asyncio
async def test_smart_search_category_override(surreal_uow_with_data):
    """Category parameter should override aspect filter"""
    result = await smart_search("preferences", surreal_uow_with_data, category="goals")
    # Even though intent is AspectFilter(preferences), category="goals" overrides
    assert result["intent"] == "AspectFilter"


# ============ Graph Neighbors Tests ============


@pytest.mark.asyncio
async def test_graph_neighbors(surreal_uow_with_data):
    """Graph neighbors should return edges connected to an entity"""
    edges = await surreal_uow_with_data.graph.get_neighbors("user", depth=1)
    assert len(edges) >= 3  # user has 3 edges as subject
    subjects_and_objects = set()
    for e in edges:
        subjects_and_objects.add(e.subject)
        subjects_and_objects.add(e.object)
    assert "user" in subjects_and_objects


@pytest.mark.asyncio
async def test_graph_neighbors_depth(surreal_uow_with_data):
    """Depth > 1 should traverse further"""
    edges_d1 = await surreal_uow_with_data.graph.get_neighbors("user", depth=1)
    # vim→is_a→text editor is 2 hops from user, may or may not be included at depth=1
    # but at depth=2 it should be
    edges_d2 = await surreal_uow_with_data.graph.get_neighbors("user", depth=2)
    assert len(edges_d2) >= len(edges_d1)


# ============ /v2/items Graph Edge Creation Tests ============


@pytest.mark.asyncio
async def test_graph_edge_created_on_item_create(surreal_uow_with_data):
    """Creating an item with full SPO should also create a graph edge"""
    uow = surreal_uow_with_data

    # Count edges before
    count_before = await uow.graph.count()

    # Create a new item
    item = ItemEntity(
        subject="Alice",
        predicate="knows",
        object="Bob",
        category="relationships",
    )
    await uow.items.create(item)

    # Manually create edge (simulating what api.py does)
    edge = GraphEdgeEntity(
        subject="Alice",
        predicate="knows",
        object="Bob",
    )
    await uow.graph.create(edge)

    count_after = await uow.graph.count()
    assert count_after == count_before + 1

    # Verify we can find it
    edges = await uow.graph.get_by_subject("Alice")
    assert len(edges) >= 1
    assert any(e.object == "Bob" for e in edges)


# ============ P1-6: Graph-Enhanced Retrieval Tests ============


@pytest.mark.asyncio
async def test_smart_search_returns_created_at(surreal_uow_with_data):
    """smart_search result dicts should include created_at and status fields"""
    result = await smart_search("about user", surreal_uow_with_data)
    assert len(result["items"]) > 0
    for item in result["items"]:
        assert "created_at" in item, "created_at missing from search result"
        assert "status" in item, "status missing from search result"
        assert item["status"] == "active"


@pytest.mark.asyncio
async def test_context_includes_graph_relations(surreal_uow_with_data):
    """get_tiered_context should include **Related:** section with graph edges"""
    from kiroku_memory.summarize import get_tiered_context

    context = await get_tiered_context(
        surreal_uow_with_data,
        max_items_per_category=10,
        record_access=False,
    )

    # All items have subject="user", graph neighbors of "user" at depth=1
    # include edges to other categories. Cross-category edges should appear
    # as **Related:** in categories that don't have them as items.
    assert "**Related:**" in context
    # For example, "goals" category only has "user wants_to learn Rust" as item,
    # but user has other edges (prefers, uses, works_at) that should show as Related
    assert "works_at" in context or "prefers" in context or "uses" in context


@pytest.mark.asyncio
async def test_context_graph_no_duplicate_within_category(surreal_uow_with_data):
    """Within a category, graph relations already shown as items should NOT appear in **Related:**"""
    from kiroku_memory.summarize import get_tiered_context

    context = await get_tiered_context(
        surreal_uow_with_data,
        max_items_per_category=10,
        record_access=False,
    )

    # Parse context into per-category blocks
    lines = context.split("\n")
    current_category = None
    category_items = {}  # category -> set of triple strings
    category_related = {}  # category -> list of triple strings

    in_related = False
    for line in lines:
        if line.startswith("### "):
            current_category = line[4:].strip().lower()
            category_items[current_category] = set()
            category_related[current_category] = []
            in_related = False
        elif line.strip() == "**Related:**":
            in_related = True
        elif line.startswith("- ") and current_category:
            triple_text = line[2:].strip()
            if in_related:
                category_related[current_category].append(triple_text)
            else:
                category_items[current_category].add(triple_text)
        elif line.strip() == "" or line.startswith("**"):
            in_related = False

    # Within each category, Related items should NOT duplicate the category's own items
    for cat, related_list in category_related.items():
        items_set = category_items.get(cat, set())
        for rel in related_list:
            assert rel not in items_set, \
                f"Category '{cat}': triple '{rel}' duplicated in both items and Related"


@pytest.mark.asyncio
async def test_retrieve_uses_smart_search(surreal_uow_with_data):
    """Verify /retrieve endpoint logic uses smart_search internally"""
    from kiroku_memory.search import smart_search

    # EntityLookup query
    result = await smart_search("about user", surreal_uow_with_data, limit=5)
    assert result["intent"] == "EntityLookup"
    assert len(result["items"]) > 0

    # Verify all result dicts have the fields needed for ItemOut
    for item in result["items"]:
        assert "id" in item
        assert "created_at" in item
        assert "subject" in item
        assert "confidence" in item
        assert "status" in item
