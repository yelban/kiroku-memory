"""Monthly re-indexing job - Recompute embeddings, reweight graph edges"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Item, Embedding, GraphEdge
from ..embedding import embed_item, generate_embedding


async def recompute_all_embeddings(
    session: AsyncSession,
    batch_size: int = 50,
) -> dict:
    """
    Recompute embeddings for all active items.

    Args:
        session: Database session
        batch_size: Items per batch

    Returns:
        Statistics dict
    """
    stats = {"processed": 0, "errors": 0}

    # Get all active items
    query = select(Item.id).where(Item.status == "active")
    result = await session.execute(query)
    item_ids = [row[0] for row in result.all()]

    for item_id in item_ids:
        try:
            await embed_item(session, item_id)
            stats["processed"] += 1
        except Exception as e:
            stats["errors"] += 1

    await session.flush()
    return stats


async def cleanup_stale_embeddings(session: AsyncSession) -> int:
    """
    Remove embeddings for archived/deleted items.

    Returns:
        Number of embeddings deleted
    """
    # Find embeddings for non-active items
    subquery = select(Item.id).where(Item.status == "active")

    # Delete embeddings not in active items
    query = delete(Embedding).where(~Embedding.item_id.in_(subquery))
    result = await session.execute(query)

    await session.flush()
    return result.rowcount


async def rebuild_graph_edges(session: AsyncSession) -> dict:
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
    delete_result = await session.execute(delete(GraphEdge))
    stats["edges_deleted"] = delete_result.rowcount

    # Get active items grouped by subject
    query = (
        select(Item)
        .where(Item.status == "active")
        .order_by(Item.subject)
    )
    result = await session.execute(query)
    items = list(result.scalars().all())

    # Build edges from co-occurring subjects
    subjects_to_items = {}
    for item in items:
        if item.subject:
            if item.subject not in subjects_to_items:
                subjects_to_items[item.subject] = []
            subjects_to_items[item.subject].append(item)

    # Create edges for items with shared objects/predicates
    seen_edges = set()
    for subject, subject_items in subjects_to_items.items():
        for item in subject_items:
            if item.object:
                # Create edge: subject -> object
                edge_key = (subject, "relates_to", item.object)
                if edge_key not in seen_edges:
                    edge = GraphEdge(
                        subject=subject,
                        predicate="relates_to",
                        object=item.object,
                        weight=item.confidence,
                    )
                    session.add(edge)
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
                    edge = GraphEdge(
                        subject=s1,
                        predicate=f"shares_{category}",
                        object=s2,
                        weight=0.5,
                    )
                    session.add(edge)
                    stats["edges_created"] += 1
                    seen_edges.add(edge_key)

    await session.flush()
    return stats


async def reweight_graph_edges(session: AsyncSession) -> int:
    """
    Reweight existing graph edges based on item confidence.

    Returns:
        Number of edges updated
    """
    # Get all edges
    query = select(GraphEdge)
    result = await session.execute(query)
    edges = result.scalars().all()

    updated = 0
    for edge in edges:
        # Calculate weight based on related items
        items_query = select(func.avg(Item.confidence)).where(
            Item.status == "active",
            Item.subject == edge.subject,
        )
        avg_result = await session.execute(items_query)
        avg_confidence = avg_result.scalar() or 0.5

        if abs(edge.weight - avg_confidence) > 0.05:
            edge.weight = avg_confidence
            updated += 1

    await session.flush()
    return updated


async def optimize_indices(session: AsyncSession) -> dict:
    """
    Run database index optimization.

    Note: In production, you'd run VACUUM ANALYZE here.
    This is a placeholder for demonstration.

    Returns:
        Optimization stats
    """
    stats = {
        "items_count": 0,
        "embeddings_count": 0,
        "edges_count": 0,
    }

    # Get counts for monitoring
    items_count = await session.execute(select(func.count(Item.id)))
    stats["items_count"] = items_count.scalar() or 0

    embeddings_count = await session.execute(select(func.count(Embedding.item_id)))
    stats["embeddings_count"] = embeddings_count.scalar() or 0

    edges_count = await session.execute(select(func.count(GraphEdge.id)))
    stats["edges_count"] = edges_count.scalar() or 0

    return stats


async def run_monthly_reindex(session: AsyncSession) -> dict:
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
    stats["stale_embeddings_deleted"] = await cleanup_stale_embeddings(session)

    # Step 2: Recompute embeddings
    stats["embeddings"] = await recompute_all_embeddings(session)

    # Step 3: Rebuild graph
    stats["graph_rebuild"] = await rebuild_graph_edges(session)

    # Step 4: Reweight edges
    stats["edges_reweighted"] = await reweight_graph_edges(session)

    # Step 5: Optimize
    stats["indices"] = await optimize_indices(session)

    stats["completed_at"] = datetime.utcnow().isoformat()
    return stats
