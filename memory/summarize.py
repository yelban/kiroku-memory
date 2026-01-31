"""Summary builder - Create evolving summaries for categories"""

from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .db.config import settings
from .db.models import Item, Category


_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


SUMMARY_PROMPT = """Summarize the following facts about a user into a concise paragraph.
Focus on the most important and recent information.
Write in third person.

Category: {category}

Facts:
{facts}

Summary (2-4 sentences):"""


async def build_category_summary(
    session: AsyncSession,
    category_name: str,
    max_items: int = 50,
) -> str:
    """
    Build or update summary for a category.

    Args:
        session: Database session
        category_name: Category to summarize
        max_items: Maximum items to include

    Returns:
        Generated summary text
    """
    # Get active items in category
    query = (
        select(Item)
        .where(Item.category == category_name)
        .where(Item.status == "active")
        .order_by(Item.created_at.desc())
        .limit(max_items)
    )

    result = await session.execute(query)
    items = result.scalars().all()

    if not items:
        return f"No information available for {category_name}."

    # Format facts for prompt
    facts_text = "\n".join(
        f"- {item.subject} {item.predicate} {item.object}"
        for item in items
    )

    # Generate summary
    client = get_openai_client()
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": SUMMARY_PROMPT.format(
                category=category_name,
                facts=facts_text,
            )},
        ],
        temperature=0.3,
        max_tokens=200,
    )

    summary = response.choices[0].message.content.strip()

    # Update or create category
    cat_result = await session.execute(
        select(Category).where(Category.name == category_name)
    )
    category = cat_result.scalar_one_or_none()

    if category:
        category.summary = summary
        category.updated_at = datetime.utcnow()
    else:
        category = Category(
            name=category_name,
            summary=summary,
        )
        session.add(category)

    await session.flush()
    return summary


async def build_all_summaries(session: AsyncSession) -> dict[str, str]:
    """
    Build summaries for all categories with items.

    Returns:
        Dict of category_name -> summary
    """
    # Get distinct categories with active items
    query = (
        select(Item.category)
        .where(Item.status == "active")
        .where(Item.category.isnot(None))
        .distinct()
    )

    result = await session.execute(query)
    categories = [row[0] for row in result.all()]

    summaries = {}
    for cat_name in categories:
        summary = await build_category_summary(session, cat_name)
        summaries[cat_name] = summary

    return summaries


async def get_tiered_context(
    session: AsyncSession,
    categories: Optional[list[str]] = None,
) -> str:
    """
    Get tiered context for agent system prompt.

    Returns category summaries formatted for inclusion in prompts.

    Args:
        session: Database session
        categories: Optional list of categories to include

    Returns:
        Formatted context string
    """
    query = select(Category).order_by(Category.name)
    if categories:
        query = query.where(Category.name.in_(categories))

    result = await session.execute(query)
    cats = result.scalars().all()

    if not cats:
        return "No memory context available."

    lines = ["## User Memory Context", ""]
    for cat in cats:
        if cat.summary:
            lines.append(f"### {cat.name.title()}")
            lines.append(cat.summary)
            lines.append("")

    return "\n".join(lines)


async def get_category_stats(session: AsyncSession) -> dict[str, dict]:
    """
    Get statistics for each category.

    Returns:
        Dict of category_name -> {count, latest_update}
    """
    # Count active items per category
    count_query = (
        select(Item.category, func.count(Item.id))
        .where(Item.status == "active")
        .where(Item.category.isnot(None))
        .group_by(Item.category)
    )

    count_result = await session.execute(count_query)
    counts = {row[0]: row[1] for row in count_result.all()}

    # Get category info
    cat_query = select(Category)
    cat_result = await session.execute(cat_query)
    categories = cat_result.scalars().all()

    stats = {}
    for cat in categories:
        stats[cat.name] = {
            "count": counts.get(cat.name, 0),
            "summary_length": len(cat.summary) if cat.summary else 0,
            "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
        }

    return stats
