"""Weekly maintenance job - Compress old items, prune unused"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Item, Category, Resource


# Time decay configuration
DEFAULT_HALF_LIFE_DAYS = 30
MAX_AGE_DAYS = 90


def time_decay_score(created_at: datetime, half_life_days: int = DEFAULT_HALF_LIFE_DAYS) -> float:
    """
    Calculate time decay score using exponential decay.

    Args:
        created_at: When the item was created
        half_life_days: Days until score halves

    Returns:
        Decay score (0.0 - 1.0)
    """
    age_days = (datetime.utcnow() - created_at).days
    return 0.5 ** (age_days / half_life_days)


async def apply_time_decay(
    session: AsyncSession,
    half_life_days: int = DEFAULT_HALF_LIFE_DAYS,
) -> int:
    """
    Apply time decay to item confidence scores.

    Args:
        session: Database session
        half_life_days: Days until confidence halves

    Returns:
        Number of items updated
    """
    query = select(Item).where(Item.status == "active")
    result = await session.execute(query)
    items = result.scalars().all()

    updated = 0
    for item in items:
        decay = time_decay_score(item.created_at, half_life_days)
        new_confidence = item.confidence * decay

        # Only update if significantly changed
        if abs(new_confidence - item.confidence) > 0.01:
            item.confidence = max(0.1, new_confidence)  # Minimum 0.1
            updated += 1

    await session.flush()
    return updated


async def archive_old_items(
    session: AsyncSession,
    max_age_days: int = MAX_AGE_DAYS,
    min_confidence: float = 0.2,
) -> int:
    """
    Archive items that are too old and have low confidence.

    Args:
        session: Database session
        max_age_days: Maximum age before considering archival
        min_confidence: Items below this confidence get archived

    Returns:
        Number of items archived
    """
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)

    query = select(Item).where(
        and_(
            Item.status == "active",
            Item.created_at < cutoff,
            Item.confidence < min_confidence,
        )
    )

    result = await session.execute(query)
    items = result.scalars().all()

    archived = 0
    for item in items:
        item.status = "archived"
        archived += 1

    await session.flush()
    return archived


async def compress_similar_items(
    session: AsyncSession,
    similarity_threshold: float = 0.9,
) -> int:
    """
    Compress very similar items into one.

    Items with same subject and similar predicate/object are merged.

    Returns:
        Number of items compressed
    """
    query = (
        select(Item)
        .where(Item.status == "active")
        .order_by(Item.subject, Item.created_at.desc())
    )

    result = await session.execute(query)
    items = list(result.scalars().all())

    compressed = 0
    seen_by_subject = {}

    for item in items:
        if item.subject not in seen_by_subject:
            seen_by_subject[item.subject] = []

        # Check for similar items
        is_similar = False
        for existing in seen_by_subject[item.subject]:
            if _items_similar(existing, item, similarity_threshold):
                # Archive the older/lower confidence one
                if existing.confidence >= item.confidence:
                    item.status = "archived"
                    existing.supersedes = item.id
                else:
                    existing.status = "archived"
                    item.supersedes = existing.id
                    seen_by_subject[item.subject].remove(existing)
                    seen_by_subject[item.subject].append(item)
                compressed += 1
                is_similar = True
                break

        if not is_similar:
            seen_by_subject[item.subject].append(item)

    await session.flush()
    return compressed


def _items_similar(item1: Item, item2: Item, threshold: float) -> bool:
    """Check if two items are similar enough to merge."""
    if item1.predicate != item2.predicate:
        return False

    # Simple string similarity for object
    obj1 = (item1.object or "").lower()
    obj2 = (item2.object or "").lower()

    if obj1 == obj2:
        return True

    # Check if one contains the other
    if obj1 in obj2 or obj2 in obj1:
        return True

    return False


async def cleanup_orphaned_resources(
    session: AsyncSession,
    max_age_days: int = 180,
) -> int:
    """
    Clean up old resources that have no associated items.

    Args:
        session: Database session
        max_age_days: Only clean resources older than this

    Returns:
        Number of resources deleted
    """
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)

    # Find resources without items
    subquery = select(Item.resource_id).where(Item.resource_id.isnot(None))
    query = select(Resource).where(
        and_(
            ~Resource.id.in_(subquery),
            Resource.created_at < cutoff,
        )
    )

    result = await session.execute(query)
    orphans = result.scalars().all()

    deleted = 0
    for resource in orphans:
        await session.delete(resource)
        deleted += 1

    await session.flush()
    return deleted


async def get_memory_stats(session: AsyncSession) -> dict:
    """Get current memory statistics."""
    stats = {}

    # Item counts by status
    for status in ["active", "archived", "deleted"]:
        count_query = select(func.count(Item.id)).where(Item.status == status)
        result = await session.execute(count_query)
        stats[f"items_{status}"] = result.scalar() or 0

    # Resource count
    resource_count = await session.execute(select(func.count(Resource.id)))
    stats["resources"] = resource_count.scalar() or 0

    # Category count
    cat_count = await session.execute(select(func.count(Category.id)))
    stats["categories"] = cat_count.scalar() or 0

    # Average confidence
    avg_conf = await session.execute(
        select(func.avg(Item.confidence)).where(Item.status == "active")
    )
    stats["avg_confidence"] = round(avg_conf.scalar() or 0, 3)

    return stats


async def run_weekly_maintenance(session: AsyncSession) -> dict:
    """
    Run weekly maintenance job.

    Steps:
    1. Apply time decay to confidence scores
    2. Archive old low-confidence items
    3. Compress similar items
    4. Cleanup orphaned resources

    Returns:
        Job statistics
    """
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "before": await get_memory_stats(session),
    }

    # Step 1: Apply time decay
    stats["decayed"] = await apply_time_decay(session)

    # Step 2: Archive old items
    stats["archived"] = await archive_old_items(session)

    # Step 3: Compress similar
    stats["compressed"] = await compress_similar_items(session)

    # Step 4: Cleanup orphans
    stats["orphans_deleted"] = await cleanup_orphaned_resources(session)

    stats["after"] = await get_memory_stats(session)
    stats["completed_at"] = datetime.utcnow().isoformat()

    return stats
