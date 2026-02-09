"""Weekly maintenance job - Compress old items, prune unused"""

from collections import defaultdict
from datetime import datetime

from ..db.repositories.base import UnitOfWork
from ..db.entities import ItemEntity, GraphEdgeEntity


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
    # Ensure created_at is naive for comparison
    if created_at.tzinfo is not None:
        created_at = created_at.replace(tzinfo=None)
    age_days = (datetime.utcnow() - created_at).days
    return 0.5 ** (age_days / half_life_days)


async def apply_time_decay(
    uow: UnitOfWork,
    half_life_days: int = DEFAULT_HALF_LIFE_DAYS,
) -> int:
    """
    Apply time decay to item confidence scores.

    Args:
        uow: Unit of work
        half_life_days: Days until confidence halves

    Returns:
        Number of items updated
    """
    items = await uow.items.list(status="active", limit=10000)

    updated = 0
    for item in items:
        decay = time_decay_score(item.created_at, half_life_days)
        new_confidence = item.confidence * decay

        # Only update if significantly changed
        if abs(new_confidence - item.confidence) > 0.01:
            item.confidence = max(0.1, new_confidence)  # Minimum 0.1
            await uow.items.update(item)
            updated += 1

    return updated


# Confidence propagation configuration
PROPAGATION_STRENGTH = 0.15
DISTANCE_DISCOUNT = {1: 1.0, 2: 0.5}
MIN_CHANGE_THRESHOLD = 0.01
MAX_PROPAGATION_DEPTH = 2


def _build_adjacency(
    edges: list[GraphEdgeEntity], max_depth: int = MAX_PROPAGATION_DEPTH
) -> dict[str, list[tuple[str, float, int]]]:
    """
    Build adjacency map from graph edges with multi-hop expansion.

    Returns:
        dict mapping entity -> [(neighbor_entity, edge_weight, distance)]
    """
    # 1-hop direct neighbors
    direct: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for edge in edges:
        direct[edge.subject].append((edge.object, edge.weight))
        direct[edge.object].append((edge.subject, edge.weight))

    # Build result with distance info
    adjacency: dict[str, list[tuple[str, float, int]]] = defaultdict(list)

    for entity, neighbors in direct.items():
        seen = {entity}
        # 1-hop
        for neighbor, weight in neighbors:
            if neighbor not in seen:
                adjacency[entity].append((neighbor, weight, 1))
                seen.add(neighbor)

        # 2-hop (if max_depth >= 2)
        if max_depth >= 2:
            for neighbor, _ in neighbors:
                for hop2, weight2, in direct.get(neighbor, []):
                    if hop2 not in seen:
                        adjacency[entity].append((hop2, weight2, 2))
                        seen.add(hop2)

    return dict(adjacency)


async def propagate_confidence(uow: UnitOfWork) -> int:
    """
    Propagate confidence through the knowledge graph.

    High-confidence neighbors boost item confidence;
    low-confidence neighbors pull it down.

    Returns:
        Number of items updated
    """
    items = await uow.items.list(status="active", limit=10000)
    edges = await uow.graph.list_all()

    if not edges:
        return 0

    adjacency = _build_adjacency(edges)

    # Build entity -> items mapping (using canonical_subject)
    entity_items: dict[str, list[ItemEntity]] = defaultdict(list)
    for item in items:
        if item.meta_about is not None:
            continue
        canonical = item.canonical_subject or item.canonical_object
        if canonical:
            entity_items[canonical].append(item)

    # Build entity -> avg confidence for neighbor lookups
    entity_confidence: dict[str, float] = {}
    for entity, eitems in entity_items.items():
        if eitems:
            entity_confidence[entity] = sum(i.confidence for i in eitems) / len(eitems)

    updated = 0
    for item in items:
        if item.meta_about is not None:
            continue

        canonical = item.canonical_subject or item.canonical_object
        if not canonical or canonical not in adjacency:
            continue

        neighbors = adjacency[canonical]
        if not neighbors:
            continue

        # Weighted average of neighbor confidence
        total_weight = 0.0
        weighted_sum = 0.0
        for neighbor_entity, edge_weight, distance in neighbors:
            if neighbor_entity not in entity_confidence:
                continue
            discount = DISTANCE_DISCOUNT.get(distance, 0.0)
            w = edge_weight * discount
            weighted_sum += entity_confidence[neighbor_entity] * w
            total_weight += w

        if total_weight == 0:
            continue

        neighbor_signal = weighted_sum / total_weight
        new_confidence = item.confidence * (1 - PROPAGATION_STRENGTH) + neighbor_signal * PROPAGATION_STRENGTH
        new_confidence = max(0.1, min(1.0, new_confidence))

        if abs(new_confidence - item.confidence) < MIN_CHANGE_THRESHOLD:
            continue

        item.confidence = new_confidence
        await uow.items.update(item)
        updated += 1

    return updated


async def archive_old_items(
    uow: UnitOfWork,
    max_age_days: int = MAX_AGE_DAYS,
    min_confidence: float = 0.2,
) -> int:
    """
    Archive items that are too old and have low confidence.

    Args:
        uow: Unit of work
        max_age_days: Maximum age before considering archival
        min_confidence: Items below this confidence get archived

    Returns:
        Number of items archived
    """
    items = await uow.items.list_old_low_confidence(max_age_days, min_confidence)

    archived = 0
    for item in items:
        await uow.items.update_status(item.id, "archived")
        archived += 1

    return archived


async def compress_similar_items(
    uow: UnitOfWork,
    similarity_threshold: float = 0.9,
) -> int:
    """
    Compress very similar items into one.

    Items with same subject and similar predicate/object are merged.

    Returns:
        Number of items compressed
    """
    items = await uow.items.list(status="active", limit=10000)

    # Sort by subject and created_at descending
    items_sorted = sorted(items, key=lambda x: (x.subject or "", x.created_at), reverse=True)

    compressed = 0
    seen_by_subject = {}

    for item in items_sorted:
        subject = item.subject or ""
        if subject not in seen_by_subject:
            seen_by_subject[subject] = []

        # Check for similar items
        is_similar = False
        for existing in seen_by_subject[subject]:
            if _items_similar(existing, item, similarity_threshold):
                # Archive the older/lower confidence one
                if existing.confidence >= item.confidence:
                    await uow.items.update_status(item.id, "archived")
                    existing.supersedes = item.id
                    await uow.items.update(existing)
                else:
                    await uow.items.update_status(existing.id, "archived")
                    item.supersedes = existing.id
                    await uow.items.update(item)
                    seen_by_subject[subject].remove(existing)
                    seen_by_subject[subject].append(item)
                compressed += 1
                is_similar = True
                break

        if not is_similar:
            seen_by_subject[subject].append(item)

    return compressed


def _items_similar(item1: ItemEntity, item2: ItemEntity, threshold: float) -> bool:
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
    uow: UnitOfWork,
    max_age_days: int = 180,
) -> int:
    """
    Clean up old resources that have no associated items.

    Args:
        uow: Unit of work
        max_age_days: Only clean resources older than this

    Returns:
        Number of resources deleted
    """
    return await uow.resources.delete_orphaned(max_age_days)


async def get_memory_stats(uow: UnitOfWork) -> dict:
    """Get current memory statistics."""
    stats = await uow.items.get_stats_by_status()

    # Resource count
    stats["resources"] = await uow.resources.count()

    # Category count (derived from items)
    cat_names = await uow.items.list_distinct_categories(status="active")
    stats["categories"] = len(cat_names)

    # Average confidence
    stats["avg_confidence"] = await uow.items.get_avg_confidence(status="active")

    return stats


async def run_weekly_maintenance(uow: UnitOfWork) -> dict:
    """
    Run weekly maintenance job.

    Steps:
    1. Apply time decay to confidence scores
    2. Propagate confidence through knowledge graph
    3. Archive old low-confidence items
    4. Compress similar items
    5. Cleanup orphaned resources

    Returns:
        Job statistics
    """
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "before": await get_memory_stats(uow),
    }

    # Step 1: Apply time decay
    stats["decayed"] = await apply_time_decay(uow)

    # Step 2: Propagate confidence through knowledge graph
    stats["propagated"] = await propagate_confidence(uow)

    # Step 3: Archive old items
    stats["archived"] = await archive_old_items(uow)

    # Step 4: Compress similar
    stats["compressed"] = await compress_similar_items(uow)

    # Step 5: Cleanup orphans
    stats["orphans_deleted"] = await cleanup_orphaned_resources(uow)

    stats["after"] = await get_memory_stats(uow)
    stats["completed_at"] = datetime.utcnow().isoformat()

    return stats
