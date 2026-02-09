"""Monthly re-indexing job - Recompute embeddings, reweight graph edges"""

from datetime import datetime
from uuid import UUID

from ..db.repositories.base import UnitOfWork
from ..db.entities import GraphEdgeEntity


async def recompute_all_embeddings(
    uow: UnitOfWork,
    batch_size: int = 50,
) -> dict:
    """
    Recompute embeddings for all active items.

    Args:
        uow: Unit of work
        batch_size: Items per batch

    Returns:
        Statistics dict
    """
    from ..embedding.factory import get_embedding_provider
    from ..db.config import settings

    stats = {"processed": 0, "errors": 0}

    # Get all active items (exclude meta items)
    all_items = await uow.items.list(status="active", limit=100000)
    items = [it for it in all_items if it.meta_about is None]

    if not items:
        return stats

    provider = get_embedding_provider()
    storage_dim = settings.embedding_dimensions

    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        try:
            texts = [
                provider.build_text_for_item(
                    it.subject, it.predicate, it.object, it.category
                )
                for it in batch
            ]
            results = await provider.embed_batch(texts)

            embeddings: dict[UUID, list[float]] = {}
            for item, result in zip(batch, results):
                vec = result.vector
                if len(vec) != storage_dim:
                    vec = provider.adapt_vector(vec, storage_dim)
                embeddings[item.id] = vec

            await uow.embeddings.batch_upsert(embeddings)
            stats["processed"] += len(batch)
        except Exception:
            stats["errors"] += len(batch)

    return stats


async def cleanup_stale_embeddings(uow: UnitOfWork) -> int:
    """
    Remove embeddings for archived/deleted items.

    Returns:
        Number of embeddings deleted
    """
    # Get active item IDs
    active_ids = await uow.items.list_all_ids(status="active")

    # Delete embeddings not in active items
    return await uow.embeddings.delete_stale(active_ids)


async def rebuild_graph_edges(uow: UnitOfWork) -> dict:
    """
    Rebuild knowledge graph edges from items.

    Creates edges based on:
    - Items with same subject (co-occurrence)
    - Items in same category (category relation)

    Returns:
        Statistics dict
    """
    stats = {"edges_created": 0, "edges_deleted": 0}

    # Clear existing edges
    stats["edges_deleted"] = await uow.graph.delete_all()

    # Get active items
    items = await uow.items.list(status="active", limit=10000)

    # Build edges from co-occurring subjects
    subjects_to_items = {}
    for item in items:
        if item.subject:
            if item.subject not in subjects_to_items:
                subjects_to_items[item.subject] = []
            subjects_to_items[item.subject].append(item)

    # Create edges for items with shared objects/predicates
    seen_edges = set()
    edges_to_create = []

    for subject, subject_items in subjects_to_items.items():
        for item in subject_items:
            if item.object:
                # Create edge: subject -> object
                edge_key = (subject, "relates_to", item.object)
                if edge_key not in seen_edges:
                    edge = GraphEdgeEntity(
                        subject=subject,
                        predicate="relates_to",
                        object=item.object,
                        weight=item.confidence,
                    )
                    edges_to_create.append(edge)
                    stats["edges_created"] += 1
                    seen_edges.add(edge_key)

    # Create category-based edges
    categories_to_subjects = {}
    for item in items:
        if item.category and item.subject:
            if item.category not in categories_to_subjects:
                categories_to_subjects[item.category] = set()
            categories_to_subjects[item.category].add(item.subject)

    for category, subjects in categories_to_subjects.items():
        subjects_list = list(subjects)
        for i, s1 in enumerate(subjects_list):
            for s2 in subjects_list[i+1:]:
                edge_key = (s1, f"shares_{category}", s2)
                if edge_key not in seen_edges:
                    edge = GraphEdgeEntity(
                        subject=s1,
                        predicate=f"shares_{category}",
                        object=s2,
                        weight=0.5,
                    )
                    edges_to_create.append(edge)
                    stats["edges_created"] += 1
                    seen_edges.add(edge_key)

    # Batch create edges
    if edges_to_create:
        await uow.graph.create_many(edges_to_create)

    return stats


async def reweight_graph_edges(uow: UnitOfWork) -> int:
    """
    Reweight existing graph edges based on item confidence.

    Returns:
        Number of edges updated
    """
    # Get all edges
    edges = await uow.graph.list_all()

    # Get average confidence per subject
    items = await uow.items.list(status="active", limit=10000)
    subject_confidences = {}
    subject_counts = {}

    for item in items:
        if item.subject:
            if item.subject not in subject_confidences:
                subject_confidences[item.subject] = 0.0
                subject_counts[item.subject] = 0
            subject_confidences[item.subject] += item.confidence
            subject_counts[item.subject] += 1

    # Calculate averages
    subject_avg = {
        s: subject_confidences[s] / subject_counts[s]
        for s in subject_confidences
    }

    updated = 0
    for edge in edges:
        avg_confidence = subject_avg.get(edge.subject, 0.5)

        if abs(edge.weight - avg_confidence) > 0.05:
            if await uow.graph.update_weight(edge.subject, edge.predicate, edge.object, avg_confidence):
                updated += 1

    return updated


async def optimize_indices(uow: UnitOfWork) -> dict:
    """
    Run database index optimization.

    Note: In production, you'd run VACUUM ANALYZE here.
    This is a placeholder for demonstration.

    Returns:
        Optimization stats
    """
    stats = {
        "items_count": await uow.items.count(),
        "embeddings_count": await uow.embeddings.count(),
        "edges_count": await uow.graph.count(),
    }

    return stats


async def run_monthly_reindex(uow: UnitOfWork) -> dict:
    """
    Run monthly re-indexing job.

    Steps:
    1. Cleanup stale embeddings
    2. Recompute all embeddings
    3. Rebuild graph edges
    4. Reweight graph edges
    5. Optimize indices

    Returns:
        Job statistics
    """
    stats = {
        "started_at": datetime.utcnow().isoformat(),
    }

    # Step 1: Cleanup stale embeddings
    stats["stale_embeddings_deleted"] = await cleanup_stale_embeddings(uow)

    # Step 2: Recompute embeddings
    stats["embeddings"] = await recompute_all_embeddings(uow)

    # Step 3: Rebuild graph
    stats["graph_rebuild"] = await rebuild_graph_edges(uow)

    # Step 4: Reweight edges
    stats["edges_reweighted"] = await reweight_graph_edges(uow)

    # Step 5: Optimize
    stats["indices"] = await optimize_indices(uow)

    stats["completed_at"] = datetime.utcnow().isoformat()
    return stats
