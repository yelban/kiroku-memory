"""Conflict resolver - Detect and resolve contradicting facts"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .db.config import settings
from .db.models import Item


_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


CONFLICT_PROMPT = """Do these two facts conflict with each other?

Fact 1:
- Subject: {s1}
- Predicate: {p1}
- Object: {o1}

Fact 2:
- Subject: {s2}
- Predicate: {p2}
- Object: {o2}

Answer only YES or NO."""


async def check_conflict(item1: Item, item2: Item, use_llm: bool = True) -> bool:
    """
    Check if two items conflict.

    Args:
        item1: First item
        item2: Second item
        use_llm: Whether to use LLM for conflict detection

    Returns:
        True if items conflict
    """
    # Same subject and predicate but different object = likely conflict
    if (
        item1.subject == item2.subject
        and item1.predicate == item2.predicate
        and item1.object != item2.object
    ):
        if not use_llm:
            return True

        # Use LLM to verify
        client = get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": CONFLICT_PROMPT.format(
                    s1=item1.subject, p1=item1.predicate, o1=item1.object,
                    s2=item2.subject, p2=item2.predicate, o2=item2.object,
                )},
            ],
            temperature=0,
            max_tokens=5,
        )
        answer = response.choices[0].message.content.strip().upper()
        return answer == "YES"

    return False


async def find_conflicts(
    session: AsyncSession,
    item_id: UUID,
) -> list[Item]:
    """
    Find items that conflict with the given item.

    Args:
        session: Database session
        item_id: UUID of item to check

    Returns:
        List of conflicting items
    """
    item = await session.get(Item, item_id)
    if not item:
        return []

    # Find items with same subject and predicate
    query = select(Item).where(
        and_(
            Item.id != item_id,
            Item.subject == item.subject,
            Item.predicate == item.predicate,
            Item.status == "active",
        )
    )

    result = await session.execute(query)
    candidates = result.scalars().all()

    conflicts = []
    for candidate in candidates:
        if await check_conflict(item, candidate, use_llm=False):
            conflicts.append(candidate)

    return conflicts


async def resolve_conflict(
    session: AsyncSession,
    new_item_id: UUID,
    old_item_id: UUID,
) -> None:
    """
    Resolve conflict by archiving old item and linking to new.

    Args:
        session: Database session
        new_item_id: UUID of new (winning) item
        old_item_id: UUID of old (losing) item
    """
    old_item = await session.get(Item, old_item_id)
    new_item = await session.get(Item, new_item_id)

    if not old_item or not new_item:
        raise ValueError("Item not found")

    # Archive old item
    old_item.status = "archived"

    # Link new item to old (supersedes)
    new_item.supersedes = old_item_id

    await session.flush()


async def auto_resolve_conflicts(
    session: AsyncSession,
    item_id: UUID,
    strategy: str = "recency",
) -> int:
    """
    Automatically resolve conflicts for an item.

    Strategies:
    - recency: Newer item wins (default)
    - confidence: Higher confidence wins
    - manual: Don't auto-resolve (returns 0)

    Args:
        session: Database session
        item_id: UUID of item to check
        strategy: Resolution strategy

    Returns:
        Number of conflicts resolved
    """
    if strategy == "manual":
        return 0

    item = await session.get(Item, item_id)
    if not item:
        return 0

    conflicts = await find_conflicts(session, item_id)

    resolved = 0
    for conflict in conflicts:
        if strategy == "recency":
            # Newer wins
            if item.created_at > conflict.created_at:
                await resolve_conflict(session, item_id, conflict.id)
            else:
                await resolve_conflict(session, conflict.id, item_id)
            resolved += 1

        elif strategy == "confidence":
            # Higher confidence wins
            if item.confidence >= conflict.confidence:
                await resolve_conflict(session, item_id, conflict.id)
            else:
                await resolve_conflict(session, conflict.id, item_id)
            resolved += 1

    return resolved


async def list_archived_conflicts(
    session: AsyncSession,
    limit: int = 100,
) -> list[tuple[Item, Item]]:
    """
    List archived items with their superseding items.

    Returns:
        List of (archived_item, superseding_item) tuples
    """
    query = (
        select(Item)
        .where(Item.status == "archived")
        .order_by(Item.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    archived = result.scalars().all()

    pairs = []
    for item in archived:
        # Find item that supersedes this one
        superseding_query = select(Item).where(Item.supersedes == item.id)
        superseding_result = await session.execute(superseding_query)
        superseding = superseding_result.scalar_one_or_none()
        if superseding:
            pairs.append((item, superseding))

    return pairs
