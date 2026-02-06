"""Category classifier - Assign items to categories"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from openai import AsyncOpenAI

from .db.config import settings
from .db.repositories.base import UnitOfWork
from .db.entities import ItemEntity, CategoryEntity


# Default categories
DEFAULT_CATEGORIES = [
    ("preferences", "User preferences, settings, and personal choices"),
    ("facts", "Factual information about the user or their environment"),
    ("events", "Past or scheduled events, activities, appointments"),
    ("relationships", "People, organizations, and their connections"),
    ("skills", "Abilities, expertise, knowledge areas"),
    ("goals", "Objectives, plans, aspirations"),
]

# Initialize OpenAI client (lazy)
_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


CLASSIFY_PROMPT = """Classify the following fact into one of these categories:

Categories:
{categories}

Fact:
- Subject: {subject}
- Predicate: {predicate}
- Object: {object}

Return only the category name, nothing else."""


async def ensure_default_categories(uow: UnitOfWork) -> None:
    """No-op. Kept for backward compatibility. Categories are derived from items."""
    pass


async def classify_item(
    uow: UnitOfWork,
    item_id: UUID,
    use_llm: bool = True,
) -> str:
    """
    Classify an item into a category.

    Args:
        uow: Unit of work
        item_id: UUID of item to classify
        use_llm: Whether to use LLM for classification

    Returns:
        Category name
    """
    item = await uow.items.get(item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found")

    if item.category:
        return item.category

    if not use_llm:
        # Simple rule-based classification
        category = _rule_based_classify(item)
        item.category = category
        await uow.items.update(item)
        return category

    # LLM classification
    client = get_openai_client()
    categories_text = "\n".join(f"- {name}: {desc}" for name, desc in DEFAULT_CATEGORIES)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": CLASSIFY_PROMPT.format(
                categories=categories_text,
                subject=item.subject or "",
                predicate=item.predicate or "",
                object=item.object or "",
            )},
        ],
        temperature=0,
        max_tokens=20,
    )

    category = response.choices[0].message.content.strip().lower()

    # Validate category
    valid_names = [name for name, _ in DEFAULT_CATEGORIES]
    if category not in valid_names:
        category = _rule_based_classify(item)

    # Update item
    item.category = category
    await uow.items.update(item)

    return category


def _rule_based_classify(item: ItemEntity) -> str:
    """Simple rule-based classification fallback."""
    predicate = (item.predicate or "").lower()

    if any(w in predicate for w in ["prefer", "like", "want", "use"]):
        return "preferences"
    if any(w in predicate for w in ["know", "met", "friend", "colleague"]):
        return "relationships"
    if any(w in predicate for w in ["can", "skill", "expert", "learn"]):
        return "skills"
    if any(w in predicate for w in ["plan", "goal", "want to", "will"]):
        return "goals"
    if any(w in predicate for w in ["attend", "schedule", "meet", "event"]):
        return "events"

    return "facts"


async def reclassify_items(
    uow: UnitOfWork,
    category: Optional[str] = None,
    limit: int = 100,
) -> int:
    """
    Reclassify items that may have wrong categories.

    Args:
        uow: Unit of work
        category: Only reclassify items in this category
        limit: Maximum items to process

    Returns:
        Number of items reclassified
    """
    items = await uow.items.list(category=category, status="active", limit=limit)

    count = 0
    for item in items:
        old_category = item.category
        item.category = None  # Reset to force reclassification
        await uow.items.update(item)
        new_category = await classify_item(uow, item.id)
        if new_category != old_category:
            count += 1

    return count
