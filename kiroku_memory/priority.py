"""Priority configuration and scoring for category ordering.

Hybrid priority model:
- Static base weights (configurable priority order)
- Dynamic factors based on usage frequency and recency
- Final priority = static_weight × dynamic_factor
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import exp
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PriorityConfig:
    """Configuration for category priority scoring."""

    # Static priority weights (higher = more important)
    # Order: preferences > facts > goals > skills > relationships > events
    static_weights: dict[str, float] = None

    # Dynamic factor parameters
    usage_window_days: int = 30  # Rolling window for usage frequency
    usage_norm: int = 10  # Normalize usage count (count / norm, capped at 1.0)
    usage_weight: float = 0.3  # Weight for usage factor in dynamic score

    recency_half_life_days: float = 14.0  # Half-life for recency decay
    recency_weight: float = 0.2  # Weight for recency factor in dynamic score

    # Fallback weight for unknown categories
    default_weight: float = 0.5

    def __post_init__(self):
        if self.static_weights is None:
            self.static_weights = {
                "preferences": 1.0,    # Most useful for personalization
                "facts": 0.9,          # Core user information
                "goals": 0.7,          # User objectives
                "skills": 0.6,         # User abilities
                "relationships": 0.5,  # Social context
                "events": 0.4,         # Least critical for context
            }


# Global default config
DEFAULT_PRIORITY_CONFIG = PriorityConfig()


@dataclass
class CategoryStats:
    """Statistics for a category used in priority scoring."""

    name: str
    item_count: int = 0
    last_item_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = 0  # Access count in rolling window


def calculate_priority(
    stats: CategoryStats,
    config: PriorityConfig = None,
    now: datetime = None,
) -> float:
    """
    Calculate priority score for a category.

    Priority = static_weight × dynamic_factor

    Dynamic factor includes:
    - Usage frequency (how often the category is accessed)
    - Recency (when was the category last updated)

    Args:
        stats: Category statistics
        config: Priority configuration
        now: Current time (for testing)

    Returns:
        Priority score (higher = more important)
    """
    if config is None:
        config = DEFAULT_PRIORITY_CONFIG
    if now is None:
        now = datetime.utcnow()

    # Get static weight
    static_weight = config.static_weights.get(stats.name, config.default_weight)

    # Calculate usage score (0..1)
    usage_score = min(1.0, stats.usage_count / config.usage_norm) if config.usage_norm > 0 else 0.0

    # Calculate recency score (0..1) using exponential decay
    # Use the most recent of updated_at and last_item_at
    last_update = stats.updated_at
    if stats.last_item_at:
        if last_update is None or stats.last_item_at > last_update:
            last_update = stats.last_item_at

    if last_update:
        age_days = (now - last_update).total_seconds() / 86400
        recency_score = exp(-age_days / config.recency_half_life_days)
    else:
        recency_score = 0.0

    # Calculate dynamic factor
    # Base of 1.0 ensures static weight is minimum
    dynamic_factor = (
        1.0
        + config.usage_weight * usage_score
        + config.recency_weight * recency_score
    )

    return static_weight * dynamic_factor


def sort_categories_by_priority(
    categories: list[CategoryStats],
    config: PriorityConfig = None,
    now: datetime = None,
) -> list[CategoryStats]:
    """
    Sort categories by priority (highest first).

    Args:
        categories: List of category statistics
        config: Priority configuration
        now: Current time (for testing)

    Returns:
        Sorted list of categories
    """
    if config is None:
        config = DEFAULT_PRIORITY_CONFIG
    if now is None:
        now = datetime.utcnow()

    return sorted(
        categories,
        key=lambda c: (calculate_priority(c, config, now), c.name),
        reverse=True,
    )


async def gather_category_stats(
    session: AsyncSession,
    config: PriorityConfig = None,
) -> list[CategoryStats]:
    """
    Gather statistics for all categories in a single efficient query.

    Args:
        session: Database session
        config: Priority configuration

    Returns:
        List of CategoryStats for all categories with items
    """
    # Import here to avoid circular imports
    from .db.models import Item, Category, CategoryAccess

    if config is None:
        config = DEFAULT_PRIORITY_CONFIG

    now = datetime.utcnow()
    window_start = now - timedelta(days=config.usage_window_days)

    # Query 1: Get item counts and last item timestamp per category
    item_stats_query = (
        select(
            Item.category,
            func.count(Item.id).label("item_count"),
            func.max(Item.created_at).label("last_item_at"),
        )
        .where(Item.status == "active")
        .where(Item.category.isnot(None))
        .group_by(Item.category)
    )
    item_stats_result = await session.execute(item_stats_query)
    item_stats = {row.category: (row.item_count, row.last_item_at) for row in item_stats_result}

    # Query 2: Get usage counts per category in rolling window
    usage_query = (
        select(
            CategoryAccess.category,
            func.count(CategoryAccess.id).label("usage_count"),
        )
        .where(CategoryAccess.accessed_at >= window_start)
        .group_by(CategoryAccess.category)
    )
    usage_result = await session.execute(usage_query)
    usage_counts = {row.category: row.usage_count for row in usage_result}

    # Query 3: Get category metadata (updated_at)
    cat_query = select(Category)
    cat_result = await session.execute(cat_query)
    categories = {cat.name: cat for cat in cat_result.scalars()}

    # Combine all stats
    all_category_names = set(item_stats.keys()) | set(categories.keys())
    stats_list = []

    for name in all_category_names:
        item_count, last_item_at = item_stats.get(name, (0, None))
        usage_count = usage_counts.get(name, 0)
        cat = categories.get(name)
        updated_at = cat.updated_at if cat else None

        stats_list.append(CategoryStats(
            name=name,
            item_count=item_count,
            last_item_at=last_item_at,
            updated_at=updated_at,
            usage_count=usage_count,
        ))

    return stats_list


async def record_category_access(
    session: AsyncSession,
    category_names: list[str],
    source: str = "context",
) -> None:
    """
    Record access events for categories.

    Args:
        session: Database session
        category_names: List of category names that were accessed
        source: Source of access (e.g., "context", "recall", "api")
    """
    from .db.models import CategoryAccess

    now = datetime.utcnow()
    for name in category_names:
        access = CategoryAccess(
            category=name,
            accessed_at=now,
            source=source,
        )
        session.add(access)

    await session.flush()


# ============ UnitOfWork versions ============

async def gather_category_stats_uow(
    uow,
    config: PriorityConfig = None,
) -> list[CategoryStats]:
    """
    Gather statistics for all categories using UnitOfWork.

    Args:
        uow: Unit of work
        config: Priority configuration

    Returns:
        List of CategoryStats for all categories with items
    """
    if config is None:
        config = DEFAULT_PRIORITY_CONFIG

    now = datetime.utcnow()
    window_start = now - timedelta(days=config.usage_window_days)

    # Get item counts per category
    item_counts = await uow.categories.count_items_per_category(status="active")

    # Get usage counts per category in rolling window
    usage_counts = await uow.category_accesses.count_by_category(since=window_start)

    # Get category metadata
    categories_list = await uow.categories.list()
    categories = {cat.name: cat for cat in categories_list}

    # Get last item timestamp per category (approximate via most recent items)
    # This is a simplification - for exact timestamps we'd need a new repository method
    last_item_at = {}
    for cat_name in item_counts.keys():
        items = await uow.items.list(category=cat_name, status="active", limit=1)
        if items:
            last_item_at[cat_name] = items[0].created_at

    # Combine all stats
    all_category_names = set(item_counts.keys()) | set(categories.keys())
    stats_list = []

    for name in all_category_names:
        item_count = item_counts.get(name, 0)
        usage_count = usage_counts.get(name, 0)
        cat = categories.get(name)
        updated_at = cat.updated_at if cat else None

        stats_list.append(CategoryStats(
            name=name,
            item_count=item_count,
            last_item_at=last_item_at.get(name),
            updated_at=updated_at,
            usage_count=usage_count,
        ))

    return stats_list


async def record_category_access_uow(
    uow,
    category_names: list[str],
    source: str = "context",
) -> None:
    """
    Record access events for categories using UnitOfWork.

    Args:
        uow: Unit of work
        category_names: List of category names that were accessed
        source: Source of access (e.g., "context", "recall", "api")
    """
    from .db.entities import CategoryAccessEntity

    for name in category_names:
        entity = CategoryAccessEntity(
            category=name,
            source=source,
        )
        await uow.category_accesses.create(entity)
