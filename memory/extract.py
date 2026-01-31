"""Fact extraction engine - Convert messages into atomic items"""

from typing import Optional
from uuid import UUID

from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .db.config import settings
from .db.models import Item, Resource


# Initialize OpenAI client (lazy)
_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


class ExtractedFact(BaseModel):
    """A single extracted fact"""
    subject: str
    predicate: str
    object: str
    category: str
    confidence: float = 1.0


class ExtractionResult(BaseModel):
    """Result of fact extraction"""
    facts: list[ExtractedFact]


EXTRACTION_PROMPT = """Extract atomic facts from the following text.

For each fact, identify:
- subject: The entity the fact is about
- predicate: The relationship or property
- object: The value or related entity
- category: One of [preferences, facts, events, relationships, skills, goals]
- confidence: 0.0-1.0 based on certainty

Return JSON array of facts. Only extract clear, verifiable facts.
If no facts can be extracted, return empty array.

Text:
{text}

Return only valid JSON:"""


async def extract_facts(text: str) -> list[ExtractedFact]:
    """
    Extract atomic facts from text using LLM.

    Args:
        text: Input text to extract facts from

    Returns:
        List of extracted facts
    """
    client = get_openai_client()

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You extract structured facts from text. Return only valid JSON."},
            {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    content = response.choices[0].message.content
    if not content:
        return []

    import json
    try:
        data = json.loads(content)
        facts_data = data.get("facts", data) if isinstance(data, dict) else data
        if not isinstance(facts_data, list):
            facts_data = [facts_data] if facts_data else []
        return [ExtractedFact(**f) for f in facts_data if isinstance(f, dict)]
    except (json.JSONDecodeError, ValueError):
        return []


async def extract_and_store(
    session: AsyncSession,
    resource_id: UUID,
) -> list[UUID]:
    """
    Extract facts from a resource and store as items.

    Args:
        session: Database session
        resource_id: UUID of resource to extract from

    Returns:
        List of created item UUIDs
    """
    # Get resource
    resource = await session.get(Resource, resource_id)
    if not resource:
        raise ValueError(f"Resource {resource_id} not found")

    # Extract facts
    facts = await extract_facts(resource.content)

    # Create items
    item_ids = []
    for fact in facts:
        item = Item(
            resource_id=resource_id,
            subject=fact.subject,
            predicate=fact.predicate,
            object=fact.object,
            category=fact.category,
            confidence=fact.confidence,
            status="active",
        )
        session.add(item)
        await session.flush()
        item_ids.append(item.id)

    return item_ids


async def process_pending_resources(
    session: AsyncSession,
    limit: int = 100,
) -> int:
    """
    Process resources that haven't been extracted yet.

    Args:
        session: Database session
        limit: Maximum resources to process

    Returns:
        Number of resources processed
    """
    from sqlalchemy import select, exists

    # Find resources without items
    subquery = select(Item.resource_id).where(Item.resource_id.isnot(None))
    query = (
        select(Resource)
        .where(~Resource.id.in_(subquery))
        .order_by(Resource.created_at)
        .limit(limit)
    )

    result = await session.execute(query)
    resources = result.scalars().all()

    count = 0
    for resource in resources:
        try:
            await extract_and_store(session, resource.id)
            count += 1
        except Exception:
            pass

    return count
