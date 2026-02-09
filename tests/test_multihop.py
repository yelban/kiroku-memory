"""Tests for P2-8: Multi-hop Reasoning (find_paths + enhanced EntityLookup)"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from kiroku_memory.db.entities import GraphEdgeEntity, ItemEntity, GraphPath


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
async def graph_uow(surreal_uow):
    """Create graph edges for testing:
    user --prefers--> dark_mode (w=1.0)
    user --uses--> vim (w=0.9)
    vim --related_to--> neovim (w=0.8)
    dark_mode --available_in--> vscode (w=0.7)
    """
    uow = surreal_uow
    edges = [
        GraphEdgeEntity(subject="user", predicate="prefers", object="dark_mode", weight=1.0),
        GraphEdgeEntity(subject="user", predicate="uses", object="vim", weight=0.9),
        GraphEdgeEntity(subject="vim", predicate="related_to", object="neovim", weight=0.8),
        GraphEdgeEntity(subject="dark_mode", predicate="available_in", object="vscode", weight=0.7),
    ]
    await uow.graph.create_many(edges)
    return uow


# ============ find_paths Tests ============


@pytest.mark.asyncio
async def test_find_paths_depth_1(graph_uow):
    """depth=1 from user should return 2 direct paths (dark_mode, vim)"""
    paths = await graph_uow.graph.find_paths("user", max_depth=1)
    targets = {p.target for p in paths}
    assert targets == {"dark_mode", "vim"}
    for p in paths:
        assert p.source == "user"
        assert p.distance == 1
        assert len(p.edges) == 1


@pytest.mark.asyncio
async def test_find_paths_depth_2(graph_uow):
    """depth=2 from user should return 4 paths (dark_mode, vim, neovim, vscode)"""
    paths = await graph_uow.graph.find_paths("user", max_depth=2)
    targets = {p.target for p in paths}
    assert targets == {"dark_mode", "vim", "neovim", "vscode"}

    # Check 2-hop paths
    two_hop = [p for p in paths if p.distance == 2]
    assert len(two_hop) == 2
    two_hop_targets = {p.target for p in two_hop}
    assert two_hop_targets == {"neovim", "vscode"}

    # Verify hops list for neovim path
    neovim_path = next(p for p in paths if p.target == "neovim")
    assert neovim_path.hops == ["user", "vim", "neovim"]


@pytest.mark.asyncio
async def test_find_paths_with_target(graph_uow):
    """Specifying target should filter results"""
    paths = await graph_uow.graph.find_paths("user", target="neovim", max_depth=2)
    assert len(paths) == 1
    assert paths[0].target == "neovim"
    assert paths[0].distance == 2
    assert paths[0].hops == ["user", "vim", "neovim"]


@pytest.mark.asyncio
async def test_find_paths_cycle_detection(surreal_uow):
    """Cycles should not cause infinite loops"""
    uow = surreal_uow
    edges = [
        GraphEdgeEntity(subject="a", predicate="knows", object="b", weight=1.0),
        GraphEdgeEntity(subject="b", predicate="knows", object="c", weight=1.0),
        GraphEdgeEntity(subject="c", predicate="knows", object="a", weight=1.0),
    ]
    await uow.graph.create_many(edges)

    paths = await uow.graph.find_paths("a", max_depth=3)
    # Should complete without hanging; no path should revisit a node
    for p in paths:
        assert len(p.hops) == len(set(p.hops)), f"Cycle in path: {p.hops}"


@pytest.mark.asyncio
async def test_find_paths_weight_decay(graph_uow):
    """Weight should be product of edge weights along path"""
    paths = await graph_uow.graph.find_paths("user", max_depth=2)

    # user -> vim (w=0.9) -> neovim (w=0.8) => 0.72
    neovim_path = next(p for p in paths if p.target == "neovim")
    assert abs(neovim_path.weight - 0.72) < 1e-6

    # user -> dark_mode (w=1.0) -> vscode (w=0.7) => 0.7
    vscode_path = next(p for p in paths if p.target == "vscode")
    assert abs(vscode_path.weight - 0.7) < 1e-6


# ============ EntityLookup Integration Test ============


@pytest.mark.asyncio
async def test_entity_lookup_multihop(graph_uow):
    """EntityLookup should find items via 2-hop paths with lower similarity"""
    uow = graph_uow

    # Create items for direct and 2-hop targets
    from kiroku_memory.entity_resolution import resolve_entity

    items_data = [
        ("dark_mode", "is", "color scheme", "facts"),
        ("vscode", "is", "code editor", "facts"),
    ]
    for subj, pred, obj, cat in items_data:
        item = ItemEntity(
            subject=subj, predicate=pred, object=obj, category=cat,
            canonical_subject=resolve_entity(subj),
            canonical_object=resolve_entity(obj),
        )
        await uow.items.create(item)

    from kiroku_memory.search import _entity_lookup
    result = await _entity_lookup("user", uow, None, 10)

    assert result["intent"] == "EntityLookup"
    assert len(result["items"]) >= 2

    # dark_mode (1-hop, sim=0.85) should rank higher than vscode (2-hop, sim=0.7)
    dm_items = [i for i in result["items"] if i["subject"] == "dark_mode"]
    vs_items = [i for i in result["items"] if i["subject"] == "vscode"]
    assert len(dm_items) >= 1
    assert len(vs_items) >= 1
    assert dm_items[0]["similarity"] > vs_items[0]["similarity"]


# ============ API Test ============


@pytest.mark.asyncio
async def test_api_graph_paths():
    """GET /graph/paths endpoint"""
    import tempfile
    from httpx import AsyncClient, ASGITransport

    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["BACKEND"] = "surrealdb"
        os.environ["SURREAL_URL"] = f"file://{tmpdir}/apitest"

        # Force reimport to pick up new env
        import importlib
        import kiroku_memory.db.config as cfg_mod
        importlib.reload(cfg_mod)

        from kiroku_memory.api import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create items to generate graph edges
            await client.post("/v2/items", json={
                "subject": "testuser",
                "predicate": "likes",
                "object": "python",
                "category": "preferences",
            })
            await client.post("/v2/items", json={
                "subject": "python",
                "predicate": "related_to",
                "object": "fastapi",
                "category": "facts",
            })

            # Query paths
            resp = await client.get("/graph/paths", params={
                "source": "testuser",
                "max_depth": 2,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["source"] == "testuser"
            assert data["max_depth"] == 2
            assert isinstance(data["paths"], list)
            assert data["total"] == len(data["paths"])

            # Should find at least 1-hop path to python
            targets = {p["target"] for p in data["paths"]}
            assert "python" in targets

            # With target filter
            resp = await client.get("/graph/paths", params={
                "source": "testuser",
                "target": "fastapi",
                "max_depth": 2,
            })
            assert resp.status_code == 200
            data = resp.json()
            if data["total"] > 0:
                assert all(p["target"] == "fastapi" for p in data["paths"])
