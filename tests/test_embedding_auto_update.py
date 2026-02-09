"""Tests for P2-10: Embedding Auto-Update"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from kiroku_memory.db.entities import ItemEntity, GraphEdgeEntity
from kiroku_memory.embedding.base import EmbeddingResult


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


# SurrealDB HNSW index requires 1536 dimensions
EMBED_DIM = 1536


def _fake_embedding(dim=EMBED_DIM):
    """Return a fake embedding vector"""
    return [0.1] * dim


def _fake_result(dim=EMBED_DIM):
    """Return a fake EmbeddingResult"""
    return EmbeddingResult(vector=_fake_embedding(dim), model="test", dimensions=dim)


def _mock_provider(dim=EMBED_DIM):
    """Create a mock embedding provider"""
    provider = MagicMock()
    provider.build_text_for_item.return_value = "Subject: Alice | Predicate: likes | Object: Python"
    provider.embed_batch = AsyncMock(
        side_effect=lambda texts: [_fake_result(dim) for _ in texts]
    )
    provider.adapt_vector = MagicMock(side_effect=lambda vec, d: vec[:d] + [0.0] * max(0, d - len(vec)))
    provider.dimensions = dim
    return provider


async def _create_item(uow, subject="Alice", predicate="likes", obj="Python",
                       category="preferences", confidence=0.9, meta_about=None):
    """Helper: create an item"""
    from kiroku_memory.entity_resolution import resolve_entity

    item = ItemEntity(
        id=uuid4(),
        subject=subject if meta_about is None else None,
        predicate=predicate,
        object=obj,
        category="meta" if meta_about else category,
        confidence=confidence,
        canonical_subject=resolve_entity(subject) if subject and meta_about is None else None,
        canonical_object=resolve_entity(obj) if obj else None,
        meta_about=meta_about,
    )
    await uow.items.create(item)
    return item


# ─── Test 1: extract_and_store generates embeddings ───

@pytest.mark.asyncio
async def test_extract_and_store_creates_embeddings(surreal_uow):
    """extract_and_store should create embeddings for extracted items"""
    from kiroku_memory.db.entities import ResourceEntity

    resource = ResourceEntity(id=uuid4(), content="Alice likes Python", source="test")
    await surreal_uow.resources.create(resource)

    fake_facts = [
        {"subject": "Alice", "predicate": "likes", "object": "Python",
         "category": "preferences", "confidence": 0.9},
    ]

    with patch("kiroku_memory.extract.extract_facts", new_callable=AsyncMock) as mock_extract, \
         patch("kiroku_memory.embedding.factory.get_embedding_provider") as mock_get_provider, \
         patch("kiroku_memory.embedding.factory.generate_embedding", new_callable=AsyncMock) as mock_gen:

        from kiroku_memory.extract import ExtractedFact
        mock_extract.return_value = [ExtractedFact(**f) for f in fake_facts]
        mock_get_provider.return_value = _mock_provider()
        mock_gen.return_value = _fake_embedding()

        # Spy on embeddings.upsert
        original_upsert = surreal_uow.embeddings.upsert
        upsert_calls = []
        async def spy_upsert(item_id, vector):
            upsert_calls.append((item_id, vector))
            return await original_upsert(item_id, vector)
        surreal_uow.embeddings.upsert = spy_upsert

        from kiroku_memory.extract import extract_and_store
        item_ids = await extract_and_store(surreal_uow, resource.id)

        assert len(item_ids) == 1
        # Embedding should have been generated once per item
        assert mock_gen.call_count == 1
        # upsert should have been called with the item_id and vector
        assert len(upsert_calls) == 1
        assert upsert_calls[0][0] == item_ids[0]
        assert len(upsert_calls[0][1]) == EMBED_DIM

    await surreal_uow.commit()


# ─── Test 2: extract_and_store without provider doesn't error ───

@pytest.mark.asyncio
async def test_extract_and_store_no_provider_no_error(surreal_uow):
    """extract_and_store should not raise when embedding provider is unavailable"""
    from kiroku_memory.db.entities import ResourceEntity

    resource = ResourceEntity(id=uuid4(), content="Bob enjoys cooking", source="test")
    await surreal_uow.resources.create(resource)

    fake_facts = [
        {"subject": "Bob", "predicate": "enjoys", "object": "cooking",
         "category": "preferences", "confidence": 0.8},
    ]

    with patch("kiroku_memory.extract.extract_facts", new_callable=AsyncMock) as mock_extract, \
         patch("kiroku_memory.embedding.factory.get_embedding_provider", side_effect=Exception("No API key")):

        from kiroku_memory.extract import ExtractedFact, extract_and_store
        mock_extract.return_value = [ExtractedFact(**f) for f in fake_facts]

        # Should not raise
        item_ids = await extract_and_store(surreal_uow, resource.id)
        assert len(item_ids) == 1

    await surreal_uow.commit()


# ─── Test 3: meta items don't get embeddings ───

@pytest.mark.asyncio
async def test_extract_meta_items_no_embeddings(surreal_uow):
    """Meta-facts (created after embeddings) should not have embeddings.
    extract_and_store creates embeddings before meta-facts, so meta items
    are naturally excluded."""
    from kiroku_memory.db.entities import ResourceEntity

    resource = ResourceEntity(id=uuid4(), content="Carol speaks French", source="test")
    await surreal_uow.resources.create(resource)

    fake_facts = [
        {"subject": "Carol", "predicate": "speaks", "object": "French",
         "category": "skills", "confidence": 0.95},
    ]

    with patch("kiroku_memory.extract.extract_facts", new_callable=AsyncMock) as mock_extract, \
         patch("kiroku_memory.embedding.factory.get_embedding_provider") as mock_get_provider, \
         patch("kiroku_memory.embedding.factory.generate_embedding", new_callable=AsyncMock) as mock_gen:

        from kiroku_memory.extract import ExtractedFact, extract_and_store
        mock_extract.return_value = [ExtractedFact(**f) for f in fake_facts]
        mock_get_provider.return_value = _mock_provider()
        mock_gen.return_value = _fake_embedding()

        item_ids = await extract_and_store(surreal_uow, resource.id)

        # Only 1 embedding call (for the normal item, not for meta-facts)
        assert mock_gen.call_count == 1

        # Meta-fact should exist but have no embedding
        meta_facts = await surreal_uow.items.get_meta_facts(item_ids[0])
        assert len(meta_facts) >= 1
        for mf in meta_facts:
            vec = await surreal_uow.embeddings.get(mf.id)
            assert vec is None

    await surreal_uow.commit()


# ─── Test 4: recompute_all_embeddings produces embeddings ───

@pytest.mark.asyncio
async def test_recompute_all_embeddings(surreal_uow):
    """recompute_all_embeddings should generate embeddings for active items"""
    await _create_item(surreal_uow, subject="Dave", obj="Rust", category="skills")
    await _create_item(surreal_uow, subject="Dave", obj="Go", category="skills")
    await surreal_uow.commit()

    provider = _mock_provider()

    with patch("kiroku_memory.embedding.factory.get_embedding_provider", return_value=provider), \
         patch("kiroku_memory.db.config.settings") as mock_settings:
        mock_settings.embedding_dimensions = EMBED_DIM

        from kiroku_memory.jobs.monthly import recompute_all_embeddings
        stats = await recompute_all_embeddings(surreal_uow)

        assert stats["processed"] == 2
        assert stats["errors"] == 0
        assert provider.embed_batch.call_count >= 1

    await surreal_uow.commit()


# ─── Test 5: recompute_all_embeddings skips meta items ───

@pytest.mark.asyncio
async def test_recompute_skips_meta_items(surreal_uow):
    """recompute_all_embeddings should skip meta items"""
    item = await _create_item(surreal_uow, subject="Eve", obj="Java")
    await _create_item(surreal_uow, subject="meta_src", obj="gpt-4o-mini",
                       category="meta", meta_about=item.id)
    await surreal_uow.commit()

    provider = _mock_provider()

    with patch("kiroku_memory.embedding.factory.get_embedding_provider", return_value=provider), \
         patch("kiroku_memory.db.config.settings") as mock_settings:
        mock_settings.embedding_dimensions = EMBED_DIM

        from kiroku_memory.jobs.monthly import recompute_all_embeddings
        stats = await recompute_all_embeddings(surreal_uow)

        # Only 1 processed (meta item excluded)
        assert stats["processed"] == 1
        assert stats["errors"] == 0


# ─── Test 6: recompute_all_embeddings batching ───

@pytest.mark.asyncio
async def test_recompute_batching(surreal_uow):
    """recompute_all_embeddings should process items in batches"""
    for i in range(5):
        await _create_item(surreal_uow, subject=f"User{i}", obj=f"Lang{i}")
    await surreal_uow.commit()

    provider = _mock_provider()

    with patch("kiroku_memory.embedding.factory.get_embedding_provider", return_value=provider), \
         patch("kiroku_memory.db.config.settings") as mock_settings:
        mock_settings.embedding_dimensions = EMBED_DIM

        from kiroku_memory.jobs.monthly import recompute_all_embeddings
        stats = await recompute_all_embeddings(surreal_uow, batch_size=2)

        assert stats["processed"] == 5
        # 5 items / batch_size 2 = 3 batches
        assert provider.embed_batch.call_count == 3


# ─── Test 7: cleanup_stale_embeddings ───

@pytest.mark.asyncio
async def test_cleanup_stale_embeddings(surreal_uow):
    """cleanup_stale_embeddings should remove embeddings for archived items"""
    item1 = await _create_item(surreal_uow, subject="Frank", obj="C++")
    item2 = await _create_item(surreal_uow, subject="Grace", obj="Haskell")

    # Add embeddings for both
    await surreal_uow.embeddings.upsert(item1.id, _fake_embedding())
    await surreal_uow.embeddings.upsert(item2.id, _fake_embedding())
    await surreal_uow.commit()

    # Archive item2
    await surreal_uow.items.update_status(item2.id, "archived")
    await surreal_uow.commit()

    from kiroku_memory.jobs.monthly import cleanup_stale_embeddings
    deleted = await cleanup_stale_embeddings(surreal_uow)

    # item2's embedding should be cleaned up
    assert deleted >= 1

    # item1's embedding should remain
    vec1 = await surreal_uow.embeddings.get(item1.id)
    assert vec1 is not None

    # item2's embedding should be gone
    vec2 = await surreal_uow.embeddings.get(item2.id)
    assert vec2 is None


# ─── Test 8: monthly pipeline integration ───

@pytest.mark.asyncio
async def test_monthly_pipeline_embeddings(surreal_uow):
    """run_monthly_reindex should report embeddings.processed > 0"""
    await _create_item(surreal_uow, subject="Hank", obj="Elixir")
    await surreal_uow.commit()

    provider = _mock_provider()

    with patch("kiroku_memory.embedding.factory.get_embedding_provider", return_value=provider), \
         patch("kiroku_memory.db.config.settings") as mock_settings:
        mock_settings.embedding_dimensions = EMBED_DIM

        from kiroku_memory.jobs.monthly import run_monthly_reindex
        stats = await run_monthly_reindex(surreal_uow)

        assert stats["embeddings"]["processed"] >= 1
        assert stats["embeddings"]["errors"] == 0
