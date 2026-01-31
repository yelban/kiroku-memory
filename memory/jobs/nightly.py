"""Nightly consolidation job - Merge duplicates, promote hot memories"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Item, Category
from ..summarize import build_category_summary


async def find_duplicate_items(session: AsyncSession) -> list[tuple[Item, Item]]:
    """
    Find items that are likely duplicates.

    Duplicates have same subject, predicate, object but different IDs.

    Returns:
        List of (older_item, newer_item) tuples
    """
    # Find items with matching subject/predicate/object
    query = (
        select(Item)
        .where(Item.status == "active")
        .order_by(Item.subject, Item.predicate, Item.object, Item.created_at)
    )

    result = await session.execute(query)
    items = list(result.scalars().all())

    duplicates = []
    seen = {}

    for item in items:
        key = (item.subject, item.predicate, item.object)
        if key in seen:
            duplicates.append((seen[key], item))
        else:
            seen[key] = item

    return duplicates


async def merge_duplicates(
    session: AsyncSession,
    keep_newer: bool = True,
) -> int:
    """
    Merge duplicate items by archiving older ones.

    Args:
        session: Database session
        keep_newer: If True, keep newer item; else keep older

    Returns:
        Number of duplicates merged
    """
    duplicates = await find_duplicate_items(session)

    merged = 0
    for older, newer in duplicates:
        if keep_newer:
            older.status = "archived"
            newer.supersedes = older.id
            # Keep higher confidence
            if older.confidence > newer.confidence:
                newer.confidence = older.confidence
        else:
            newer.status = "archived"
            older.supersedes = newer.id
        merged += 1

    await session.flush()
    return merged


async def calculate_item_hotness(
    session: AsyncSession,
    item_id,
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
    item = await session.get(Item, item_id)
    if not item:
        return 0.0

    now = datetime.utcnow()
    lookback = now - timedelta(days=lookback_days)

    # Recency score (exponential decay)
    age_days = (now - item.created_at).days
    recency = 0.5 ** (age_days / 7)  # Half-life of 7 days

    # Related items score
    related_query = select(func.count(Item.id)).where(
        and_(
            Item.subject == item.subject,
            Item.created_at > lookback,
            Item.status == "active",
        )
    )
    related_result = await session.execute(related_query)
    related_count = related_result.scalar() or 0
    related_score = min(1.0, related_count / 10)

    # Combine scores
    hotness = (recency * 0.5 + related_score * 0.3 + item.confidence * 0.2)
    return hotness


async def promote_hot_items(
    session: AsyncSession,
    threshold: float = 0.7,
    boost_amount: float = 0.1,
) -> int:
    """
    Boost confidence of hot items.

    Args:
        session: Database session
        threshold: Minimum hotness to promote
        boost_amount: Amount to boost confidence

    Returns:
        Number of items promoted
    """
    query = select(Item).where(Item.status == "active")
    result = await session.execute(query)
    items = result.scalars().all()

    promoted = 0
    for item in items:
        hotness = await calculate_item_hotness(session, item.id)
        if hotness >= threshold:
            item.confidence = min(1.0, item.confidence + boost_amount)
            promoted += 1

    await session.flush()
    return promoted


async def update_category_summaries(session: AsyncSession) -> int:
    """
    Update summaries for categories with recent changes.

    Returns:
        Number of categories updated
    """
    # Get categories with active items
    query = (
        select(Item.category)
        .where(Item.status == "active")
        .where(Item.category.isnot(None))
        .distinct()
    )

    result = await session.execute(query)
    categories = [row[0] for row in result.all()]

    updated = 0
    for cat_name in categories:
        await build_category_summary(session, cat_name)
        updated += 1

    return updated


async def run_nightly_consolidation(session: AsyncSession) -> dict:
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
    stats["duplicates_merged"] = await merge_duplicates(session)

    # Step 2: Promote hot items
    stats["items_promoted"] = await promote_hot_items(session)

    # Step 3: Update summaries
    stats["summaries_updated"] = await update_category_summaries(session)

    stats["completed_at"] = datetime.utcnow().isoformat()
    return stats
