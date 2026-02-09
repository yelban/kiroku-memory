"""Tests for P2-9: Confidence Propagation through Knowledge Graph"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from kiroku_memory.db.entities import ItemEntity, GraphEdgeEntity
from kiroku_memory.jobs.weekly import (
    _build_adjacency,
    propagate_confidence,
    PROPAGATION_STRENGTH,
    DISTANCE_DISCOUNT,
)


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


async def _create_item(uow, subject, confidence=0.5, category="facts", meta_about=None):
    """Helper: create an item and return it"""
    from kiroku_memory.entity_resolution import resolve_entity

    item = ItemEntity(
        id=uuid4(),
        subject=subject if meta_about is None else None,
        predicate="knows",
        object="something",
        category="meta" if meta_about else category,
        confidence=confidence,
        canonical_subject=resolve_entity(subject) if subject and meta_about is None else None,
        meta_about=meta_about,
    )
    await uow.items.create(item)
    return item


async def _create_edge(uow, subject, obj, weight=1.0):
    """Helper: create a graph edge"""
    from kiroku_memory.entity_resolution import resolve_entity

    edge = GraphEdgeEntity(
        id=uuid4(),
        subject=resolve_entity(subject),
        predicate="related_to",
        object=resolve_entity(obj),
        weight=weight,
    )
    await uow.graph.create(edge)
    return edge


# ============ Unit Tests for _build_adjacency ============


def test_build_adjacency_basic():
    """1-hop neighbors appear in adjacency map"""
    edges = [
        GraphEdgeEntity(subject="a", predicate="knows", object="b", weight=1.0),
        GraphEdgeEntity(subject="b", predicate="knows", object="c", weight=0.8),
    ]
    adj = _build_adjacency(edges)

    # a -> b (1-hop), a -> c (2-hop)
    a_neighbors = adj["a"]
    assert any(n == "b" and d == 1 for n, _, d in a_neighbors)
    assert any(n == "c" and d == 2 for n, _, d in a_neighbors)


def test_build_adjacency_no_self_loop():
    """Entity should not appear as its own neighbor"""
    edges = [
        GraphEdgeEntity(subject="a", predicate="knows", object="b", weight=1.0),
    ]
    adj = _build_adjacency(edges)
    for n, _, _ in adj.get("a", []):
        assert n != "a"
    for n, _, _ in adj.get("b", []):
        assert n != "b"


# ============ Integration Tests ============


@pytest.mark.asyncio
async def test_high_confidence_neighbor_boosts(surreal_uow):
    """High-confidence neighbors should boost a low-confidence item"""
    uow = surreal_uow

    item_low = await _create_item(uow, "alpha", confidence=0.3)
    await _create_item(uow, "beta", confidence=0.9)
    await _create_edge(uow, "alpha", "beta")

    updated = await propagate_confidence(uow)
    assert updated >= 1

    refreshed = await uow.items.get(item_low.id)
    # Should be boosted: 0.3 * 0.85 + 0.9 * 0.15 = 0.39
    assert refreshed.confidence > 0.3


@pytest.mark.asyncio
async def test_low_confidence_neighbor_pulls_down(surreal_uow):
    """Low-confidence neighbors should pull down a high-confidence item"""
    uow = surreal_uow

    item_high = await _create_item(uow, "gamma", confidence=0.9)
    await _create_item(uow, "delta", confidence=0.1)
    await _create_edge(uow, "gamma", "delta")

    await propagate_confidence(uow)

    refreshed = await uow.items.get(item_high.id)
    # Should be pulled down: 0.9 * 0.85 + 0.1 * 0.15 = 0.78
    assert refreshed.confidence < 0.9


@pytest.mark.asyncio
async def test_no_neighbors_unchanged(surreal_uow):
    """Items with no graph neighbors should not change"""
    uow = surreal_uow

    item = await _create_item(uow, "isolated", confidence=0.5)

    updated = await propagate_confidence(uow)
    assert updated == 0

    refreshed = await uow.items.get(item.id)
    assert refreshed.confidence == 0.5


@pytest.mark.asyncio
async def test_2hop_weaker_influence(surreal_uow):
    """2-hop neighbors should have weaker influence than 1-hop"""
    uow = surreal_uow

    # Chain: epsilon -- zeta -- eta
    item_eps = await _create_item(uow, "epsilon", confidence=0.3)
    await _create_item(uow, "zeta", confidence=0.3)  # intermediate
    await _create_item(uow, "eta", confidence=1.0)  # high conf, 2-hop from epsilon
    await _create_edge(uow, "epsilon", "zeta")
    await _create_edge(uow, "zeta", "eta")

    await propagate_confidence(uow)

    refreshed = await uow.items.get(item_eps.id)
    # epsilon has 2 neighbors: zeta(1-hop, conf=0.3) and eta(2-hop, conf=1.0)
    # weighted avg = (0.3*1.0 + 1.0*0.5) / (1.0+0.5) = 0.8/1.5 ≈ 0.533
    # new = 0.3*0.85 + 0.533*0.15 ≈ 0.335
    assert refreshed.confidence > 0.3
    # But not as much as if eta were 1-hop
    assert refreshed.confidence < 0.4


@pytest.mark.asyncio
async def test_confidence_floor(surreal_uow):
    """Confidence should not drop below 0.1"""
    uow = surreal_uow

    item = await _create_item(uow, "theta", confidence=0.1)
    await _create_item(uow, "iota", confidence=0.1)
    await _create_edge(uow, "theta", "iota")

    await propagate_confidence(uow)

    refreshed = await uow.items.get(item.id)
    assert refreshed.confidence >= 0.1


@pytest.mark.asyncio
async def test_confidence_ceiling(surreal_uow):
    """Confidence should not exceed 1.0"""
    uow = surreal_uow

    item = await _create_item(uow, "kappa", confidence=1.0)
    await _create_item(uow, "lambda_e", confidence=1.0)
    await _create_edge(uow, "kappa", "lambda_e")

    await propagate_confidence(uow)

    refreshed = await uow.items.get(item.id)
    assert refreshed.confidence <= 1.0


@pytest.mark.asyncio
async def test_skip_small_change(surreal_uow):
    """Changes below MIN_CHANGE_THRESHOLD should be skipped"""
    uow = surreal_uow

    # Item at 0.5, neighbor also ~0.5 → blend ≈ 0.5, no update
    item = await _create_item(uow, "mu", confidence=0.5)
    await _create_item(uow, "nu", confidence=0.5)
    await _create_edge(uow, "mu", "nu")

    updated = await propagate_confidence(uow)
    assert updated == 0

    refreshed = await uow.items.get(item.id)
    assert refreshed.confidence == 0.5


@pytest.mark.asyncio
async def test_meta_items_excluded(surreal_uow):
    """Meta-facts should not participate in propagation"""
    uow = surreal_uow

    item = await _create_item(uow, "xi", confidence=0.5)
    # Create a meta-fact about item
    meta = await _create_item(uow, "xi", confidence=0.9, meta_about=item.id)

    # Even with an edge, meta items should be skipped
    await _create_edge(uow, "xi", "xi")

    updated = await propagate_confidence(uow)
    assert updated == 0

    # Meta item confidence unchanged
    meta_refreshed = await uow.items.get(meta.id)
    assert meta_refreshed.confidence == 0.9


@pytest.mark.asyncio
async def test_multi_neighbor_weighted_average(surreal_uow):
    """Multiple neighbors should contribute via weighted average"""
    uow = surreal_uow

    item = await _create_item(uow, "omicron", confidence=0.5)
    await _create_item(uow, "pi_e", confidence=0.9)
    await _create_item(uow, "rho", confidence=0.1)
    await _create_edge(uow, "omicron", "pi_e", weight=1.0)
    await _create_edge(uow, "omicron", "rho", weight=1.0)

    await propagate_confidence(uow)

    refreshed = await uow.items.get(item.id)
    # neighbor avg = (0.9 + 0.1) / 2 = 0.5
    # new = 0.5 * 0.85 + 0.5 * 0.15 = 0.5 → no change (within threshold)
    # Actually this would not update. Let's verify.
    assert refreshed.confidence == 0.5


@pytest.mark.asyncio
async def test_weekly_pipeline_includes_propagated(surreal_uow):
    """run_weekly_maintenance should include 'propagated' in stats"""
    from kiroku_memory.jobs.weekly import run_weekly_maintenance

    uow = surreal_uow

    await _create_item(uow, "sigma", confidence=0.3)
    await _create_item(uow, "tau", confidence=0.9)
    await _create_edge(uow, "sigma", "tau")

    stats = await run_weekly_maintenance(uow)
    assert "propagated" in stats
    assert isinstance(stats["propagated"], int)
    assert stats["propagated"] >= 1
