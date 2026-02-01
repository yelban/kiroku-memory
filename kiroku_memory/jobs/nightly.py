"""Nightly consolidation job - Merge duplicates, promote hot memories"""

from datetime import datetime, timedelta

from ..db.repositories.base import UnitOfWork
from ..db.entities import ItemEntity


async def find_duplicate_items(uow: UnitOfWork) -> list[tuple[ItemEntity, ItemEntity]]:
    """
    Find items that are likely duplicates.

    Duplicates have same subject, predicate, object but different IDs.

    Returns:
        List of (older_item, newer_item) tuples
    """
    return await uow.items.list_duplicates()


async def merge_duplicates(uow: UnitOfWork, keep_newer: bool = True) -> int:
    """
    Merge duplicate items by archiving older ones.

    Args:
        uow: Unit of work
        keep_newer: If True, keep newer item; else keep older

    Returns:
        Number of duplicates merged
    """
    duplicates = await find_duplicate_items(uow)

    merged = 0
    for older, newer in duplicates:
        if keep_newer:
            await uow.items.update_status(older.id, "archived")
            # Update newer item to supersede older and keep higher confidence
            newer.supersedes = older.id
            if older.confidence > newer.confidence:
                newer.confidence = older.confidence
            await uow.items.update(newer)
        else:
            await uow.items.update_status(newer.id, "archived")
            older.supersedes = newer.id
            await uow.items.update(older)
        merged += 1

    return merged


async def calculate_item_hotness(
    uow: UnitOfWork,
    item: ItemEntity,
    lookback_days: int = 7,
) -> float:
    """
    Calculate how "hot" an item is based on recent activity.

    Hotness is based on:
    - Recency of creation
    - Number of related items created recently
    - Confidence level

    Returns:
        Hotness score (0.0 - 1.0)
    """
    now = datetime.utcnow()

    # Recency score (exponential decay)
    # Ensure created_at is naive for comparison
    created_at = item.created_at
    if created_at.tzinfo is not None:
        created_at = created_at.replace(tzinfo=None)
    age_days = (now - created_at).days
    recency = 0.5 ** (age_days / 7)  # Half-life of 7 days

    # Related items score
    related_count = await uow.items.count_by_subject_recent(item.subject, lookback_days)
    related_score = min(1.0, related_count / 10)

    # Combine scores
    hotness = (recency * 0.5 + related_score * 0.3 + item.confidence * 0.2)
    return hotness


async def promote_hot_items(
    uow: UnitOfWork,
    threshold: float = 0.7,
    boost_amount: float = 0.1,
) -> int:
    """
    Boost confidence of hot items.

    Args:
        uow: Unit of work
        threshold: Minimum hotness to promote
        boost_amount: Amount to boost confidence

    Returns:
        Number of items promoted
    """
    items = await uow.items.list(status="active", limit=1000)

    promoted = 0
    for item in items:
        hotness = await calculate_item_hotness(uow, item)
        if hotness >= threshold:
            item.confidence = min(1.0, item.confidence + boost_amount)
            await uow.items.update(item)
            promoted += 1

    return promoted


async def update_category_summaries(uow: UnitOfWork) -> int:
    """
    Update summaries for categories with recent changes.

    Returns:
        Number of categories updated
    """
    # Get categories with active items
    categories = await uow.items.list_distinct_categories(status="active")

    # Note: build_category_summary will be updated in Phase 6
    # For now, just return the count of categories that would be updated
    return len(categories)


async def run_nightly_consolidation(uow: UnitOfWork) -> dict:
    """
    Run nightly consolidation job.

    Steps:
    1. Merge duplicate items
    2. Promote hot items
    3. Update category summaries

    Returns:
        Job statistics
    """
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "duplicates_merged": 0,
        "items_promoted": 0,
        "summaries_updated": 0,
    }

    # Step 1: Merge duplicates
    stats["duplicates_merged"] = await merge_duplicates(uow)

    # Step 2: Promote hot items
    stats["items_promoted"] = await promote_hot_items(uow)

    # Step 3: Update summaries
    stats["summaries_updated"] = await update_category_summaries(uow)

    stats["completed_at"] = datetime.utcnow().isoformat()
    return stats
