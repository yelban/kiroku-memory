"""Intent-driven retrieval: classify query intent and route to best strategy"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from .db.repositories.base import UnitOfWork
from .entity_resolution import resolve_entity
from .observability import logger


# ============ Intent Types ============

@dataclass
class EntityLookup:
    """Query is about a specific entity"""
    entity: str


@dataclass
class Temporal:
    """Query is about recent or time-bounded items"""
    days: int


@dataclass
class AspectFilter:
    """Query targets a specific category/aspect"""
    category: str


@dataclass
class SemanticSearch:
    """Free-text semantic search"""
    pass


QueryIntent = EntityLookup | Temporal | AspectFilter | SemanticSearch


# ============ Category Keywords ============

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "preferences": ["preferences", "偏好", "喜好", "prefer", "like", "dislike", "favorite"],
    "facts": ["facts", "事實", "資訊", "info", "information"],
    "events": ["events", "事件", "happened", "發生"],
    "relationships": ["relationships", "關係", "人脈", "knows", "friend"],
    "skills": ["skills", "技能", "能力", "can do", "expertise"],
    "goals": ["goals", "目標", "計畫", "plan", "want to", "想要"],
    "identity": ["identity", "身份", "角色", "who am i", "名字", "職業", "occupation", "role"],
    "behaviors": ["behaviors", "習慣", "行為", "routine", "habit", "慣例", "workflow", "always"],
}


# ============ Intent Classifier ============

def classify_intent(query: str) -> QueryIntent:
    """
    Rule-based intent classification (zero LLM cost).

    Patterns:
    - "about X" / "關於 X" → EntityLookup
    - "last week" / "recent" / "最近" → Temporal
    - "preferences" / "偏好" / category names → AspectFilter
    - Everything else → SemanticSearch
    """
    q = query.strip().lower()

    # Entity lookup patterns
    entity_patterns = [
        r"^about\s+(.+)$",
        r"^關於\s*(.+)$",
        r"^what (?:do (?:you|we) know about|about)\s+(.+)\??$",
        r"^(.+?)(?:是誰|是什麼|的(?:資料|資訊|記憶))[\?？]?$",
    ]
    for pattern in entity_patterns:
        m = re.match(pattern, q)
        if m:
            return EntityLookup(entity=m.group(1).strip())

    # Temporal patterns
    temporal_patterns = {
        r"(?:last|past)\s+(\d+)\s+days?": lambda m: int(m.group(1)),
        r"(?:last|past)\s+week": lambda _: 7,
        r"(?:last|past)\s+month": lambda _: 30,
        r"recent(?:ly)?": lambda _: 7,
        r"最近": lambda _: 7,
        r"今天": lambda _: 1,
        r"昨天": lambda _: 2,
        r"這週|本週": lambda _: 7,
        r"這個月|本月": lambda _: 30,
    }
    for pattern, days_fn in temporal_patterns.items():
        m = re.search(pattern, q)
        if m:
            return Temporal(days=days_fn(m))

    # Aspect/category filter
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in q:
                return AspectFilter(category=category)

    # Default: semantic search
    return SemanticSearch()


# ============ Strategy Router ============

async def smart_search(
    query: str,
    uow: UnitOfWork,
    category: Optional[str] = None,
    limit: int = 10,
    min_similarity: float = 0.5,
) -> dict:
    """
    Route query to the best retrieval strategy based on intent.

    Returns:
        dict with keys: intent (str), items (list[dict]), total (int)
    """
    intent = classify_intent(query)
    intent_name = type(intent).__name__

    logger.debug(f"Query intent: {intent_name} for '{query}'")

    if isinstance(intent, EntityLookup):
        return await _entity_lookup(intent.entity, uow, category, limit)

    elif isinstance(intent, Temporal):
        return await _temporal_search(intent.days, uow, category, limit)

    elif isinstance(intent, AspectFilter):
        # Use the classified category unless overridden
        effective_category = category or intent.category
        return await _aspect_filter(effective_category, uow, limit)

    else:
        return await _semantic_search(query, uow, category, limit, min_similarity)


async def _entity_lookup(
    entity: str,
    uow: UnitOfWork,
    category: Optional[str],
    limit: int,
) -> dict:
    """Look up an entity via graph traversal + item search."""
    canonical = resolve_entity(entity)
    results: list[dict] = []
    seen_ids: set[UUID] = set()

    # 1. Graph neighbors (use canonical form)
    try:
        edges = await uow.graph.get_neighbors(canonical, depth=1)
        for edge in edges:
            # Find items matching this edge's subject
            items = await uow.items.list_by_subject(edge.subject, status="active")
            for item in items:
                if item.id not in seen_ids and (not category or item.category == category):
                    seen_ids.add(item.id)
                    results.append(_item_to_dict(item, similarity=0.9))

            # Also find items matching the object side
            items = await uow.items.list_by_subject(edge.object, status="active")
            for item in items:
                if item.id not in seen_ids and (not category or item.category == category):
                    seen_ids.add(item.id)
                    results.append(_item_to_dict(item, similarity=0.8))
    except Exception:
        logger.debug("Graph lookup failed, falling back to item search")

    # 2. Direct item search by subject (canonical resolution happens in repository)
    try:
        items = await uow.items.list_by_subject(canonical, status="active")
        for item in items:
            if item.id not in seen_ids and (not category or item.category == category):
                seen_ids.add(item.id)
                results.append(_item_to_dict(item, similarity=1.0))
    except Exception:
        pass

    results.sort(key=lambda r: r["similarity"], reverse=True)
    results = results[:limit]

    return {"intent": "EntityLookup", "items": results, "total": len(results)}


async def _temporal_search(
    days: int,
    uow: UnitOfWork,
    category: Optional[str],
    limit: int,
) -> dict:
    """Search items within a time range."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    items = await uow.items.list(category=category, status="active", limit=limit)

    # Filter by time (items.list doesn't have a since param, filter in memory)
    results = []
    for item in items:
        # Normalize to naive UTC for comparison (SurrealDB may return aware datetimes)
        item_time = item.created_at.replace(tzinfo=None) if item.created_at.tzinfo else item.created_at
        if item_time >= since:
            results.append(_item_to_dict(item, similarity=1.0))

    return {"intent": "Temporal", "items": results, "total": len(results)}


async def _aspect_filter(
    category: str,
    uow: UnitOfWork,
    limit: int,
) -> dict:
    """Filter items by category."""
    items = await uow.items.list(category=category, status="active", limit=limit)
    results = [_item_to_dict(item, similarity=1.0) for item in items]
    return {"intent": "AspectFilter", "items": results, "total": len(results)}


async def _semantic_search(
    query: str,
    uow: UnitOfWork,
    category: Optional[str],
    limit: int,
    min_similarity: float,
) -> dict:
    """Embedding-based semantic search."""
    try:
        from .embedding.factory import generate_embedding
        query_vector = await generate_embedding(query)
        search_results = await uow.embeddings.search(
            query_vector=query_vector,
            limit=limit,
            min_similarity=min_similarity,
        )

        results = []
        for sr in search_results:
            if category and sr.item.category != category:
                continue
            results.append(_item_to_dict(sr.item, similarity=sr.similarity))

        if results:
            return {"intent": "SemanticSearch", "items": results, "total": len(results)}

        # No embedding matches — fall back to recent items
        logger.debug("Semantic search returned 0 results, falling back to recent items")

    except Exception as e:
        logger.warning(f"Semantic search failed: {e}")

    # Fallback: return recent items
    items = await uow.items.list(category=category, status="active", limit=limit)
    results = [_item_to_dict(item, similarity=0.0) for item in items]
    return {"intent": "SemanticSearch(fallback)", "items": results, "total": len(results)}


# ============ Helpers ============

def _item_to_dict(item, similarity: float = 1.0) -> dict:
    """Convert ItemEntity to dict for search results."""
    return {
        "id": item.id,
        "subject": item.subject,
        "predicate": item.predicate,
        "object": item.object,
        "category": item.category,
        "confidence": item.confidence,
        "similarity": similarity,
        "created_at": item.created_at,
        "status": item.status,
    }
