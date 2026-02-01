"""Summary builder - Create evolving summaries for categories"""

from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI

from .db.config import settings
from .db.repositories.base import UnitOfWork
from .db.entities import CategoryEntity


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
    uow: UnitOfWork,
    category_name: str,
    max_items: int = 50,
) -> str:
    """
    Build or update summary for a category.

    Args:
        uow: Unit of work
        category_name: Category to summarize
        max_items: Maximum items to include

    Returns:
        Generated summary text
    """
    # Get active items in category
    items = await uow.items.list(category=category_name, status="active", limit=max_items)

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
    category = await uow.categories.get_by_name(category_name)

    if category:
        await uow.categories.update_summary(category_name, summary)
    else:
        new_cat = CategoryEntity(
            name=category_name,
            summary=summary,
        )
        await uow.categories.create(new_cat)

    return summary


async def build_all_summaries(uow: UnitOfWork) -> dict[str, str]:
    """
    Build summaries for all categories with items.

    Returns:
        Dict of category_name -> summary
    """
    # Get distinct categories with active items
    categories = await uow.items.list_distinct_categories(status="active")

    summaries = {}
    for cat_name in categories:
        summary = await build_category_summary(uow, cat_name)
        summaries[cat_name] = summary

    return summaries


async def get_tiered_context(
    uow: UnitOfWork,
    categories: Optional[list[str]] = None,
    max_items_per_category: int = 10,
    max_chars: Optional[int] = None,
    record_access: bool = True,
) -> str:
    """
    Get tiered context for agent system prompt.

    Returns category summaries + recent items formatted for inclusion in prompts.
    Categories are ordered by priority (hybrid static + dynamic).
    Truncates by complete categories when max_chars is specified.

    Args:
        uow: Unit of work
        categories: Optional list of categories to include
        max_items_per_category: Max recent items to show per category
        max_chars: Maximum characters (truncates by complete category)
        record_access: Whether to record access events for priority tracking

    Returns:
        Formatted context string
    """
    from .priority import (
        gather_category_stats_uow,
        sort_categories_by_priority,
        record_category_access_uow,
        DEFAULT_PRIORITY_CONFIG,
    )

    # Get category stats for priority sorting
    all_stats = await gather_category_stats_uow(uow, DEFAULT_PRIORITY_CONFIG)
    sorted_stats = sort_categories_by_priority(all_stats, DEFAULT_PRIORITY_CONFIG)

    # Filter if specific categories requested
    if categories:
        sorted_stats = [s for s in sorted_stats if s.name in categories]

    if not sorted_stats:
        return "No memory context available."

    # Get category objects
    all_categories = await uow.categories.list()
    cats_by_name = {cat.name: cat for cat in all_categories}

    # Default summaries to detect if summarize has been run
    default_summaries = {
        "events": "Past or scheduled events, activities, appointments",
        "facts": "Factual information about the user or their environment",
        "goals": "Objectives, plans, aspirations",
        "preferences": "User preferences, settings, and personal choices",
        "relationships": "People, organizations, and their connections",
        "skills": "Abilities, expertise, knowledge areas",
    }

    header = "## User Memory Context\n"
    blocks = []  # List of (category_name, block_text)

    for stats in sorted_stats:
        cat = cats_by_name.get(stats.name)

        # Get recent items for this category
        items = await uow.items.list(
            category=stats.name,
            status="active",
            limit=max_items_per_category,
        )

        # Check if summary is default (not yet summarized)
        summary = cat.summary if cat else None
        is_default_summary = (
            summary == default_summaries.get(stats.name)
            or not summary
        )

        # Skip category if no items and default summary
        if not items and is_default_summary:
            continue

        block_lines = [f"### {stats.name.title()}"]

        # Show summary if it's been updated (not default)
        if summary and not is_default_summary:
            block_lines.append(summary)
            block_lines.append("")

        # Always show recent items for real-time access
        if items:
            if not is_default_summary:
                block_lines.append("**Recent:**")
            for item in items:
                obj_part = f" {item.object}" if item.object else ""
                block_lines.append(f"- {item.subject} {item.predicate}{obj_part}")
            block_lines.append("")

        blocks.append((stats.name, "\n".join(block_lines)))

    # Apply max_chars truncation by complete categories
    included_categories = []
    result_parts = [header]
    current_len = len(header)

    for cat_name, block in blocks:
        block_len = len(block) + 1  # +1 for newline separator
        if max_chars and current_len + block_len > max_chars:
            break
        result_parts.append(block)
        included_categories.append(cat_name)
        current_len += block_len

    # Record access for included categories
    if record_access and included_categories:
        await record_category_access_uow(uow, included_categories, source="context")

    return "\n".join(result_parts)


async def get_category_stats(uow: UnitOfWork) -> dict[str, dict]:
    """
    Get statistics for each category.

    Returns:
        Dict of category_name -> {count, latest_update}
    """
    # Count active items per category
    counts = await uow.categories.count_items_per_category(status="active")

    # Get category info
    categories = await uow.categories.list()

    stats = {}
    for cat in categories:
        stats[cat.name] = {
            "count": counts.get(cat.name, 0),
            "summary_length": len(cat.summary) if cat.summary else 0,
            "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
        }

    return stats
