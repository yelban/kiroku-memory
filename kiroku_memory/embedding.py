"""Embedding pipeline for semantic search"""

from typing import Optional
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .db.config import settings
from .db.models import Item, Embedding


# Initialize OpenAI client (lazy)
_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI client"""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding vector for text.

    Args:
        text: Input text to embed

    Returns:
        List of floats (1536 dimensions)
    """
    client = get_openai_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
        dimensions=settings.embedding_dimensions,
    )
    return response.data[0].embedding


async def embed_item(session: AsyncSession, item_id: UUID) -> None:
    """
    Generate and store embedding for an item.

    Args:
        session: Database session
        item_id: UUID of item to embed
    """
    # Get item
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise ValueError(f"Item {item_id} not found")

    # Build text representation
    text_parts = []
    if item.subject:
        text_parts.append(f"Subject: {item.subject}")
    if item.predicate:
        text_parts.append(f"Predicate: {item.predicate}")
    if item.object:
        text_parts.append(f"Object: {item.object}")
    if item.category:
        text_parts.append(f"Category: {item.category}")

    text = " | ".join(text_parts) if text_parts else str(item_id)

    # Generate embedding
    vector = await generate_embedding(text)

    # Upsert embedding
    existing = await session.execute(
        select(Embedding).where(Embedding.item_id == item_id)
    )
    if existing.scalar_one_or_none():
        await session.execute(
            text("UPDATE embeddings SET embedding = :vec WHERE item_id = :id"),
            {"vec": str(vector), "id": str(item_id)},
        )
    else:
        embedding = Embedding(item_id=item_id, embedding=vector)
        session.add(embedding)


async def search_similar(
    session: AsyncSession,
    query: str,
    limit: int = 10,
    min_similarity: float = 0.5,
) -> list[tuple[Item, float]]:
    """
    Search for items similar to query text.

    Args:
        session: Database session
        query: Search query text
        limit: Maximum results
        min_similarity: Minimum cosine similarity threshold

    Returns:
        List of (Item, similarity_score) tuples
    """
    # Generate query embedding
    query_vec = await generate_embedding(query)
    query_vec_str = str(query_vec)

    # Cosine similarity search using pgvector
    sql = text("""
        SELECT
            i.*,
            1 - (e.embedding <=> :query_vec::vector) as similarity
        FROM items i
        JOIN embeddings e ON i.id = e.item_id
        WHERE i.status = 'active'
          AND 1 - (e.embedding <=> :query_vec::vector) >= :min_sim
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    result = await session.execute(
        sql,
        {
            "query_vec": query_vec_str,
            "min_sim": min_similarity,
            "limit": limit,
        },
    )
    rows = result.fetchall()

    # Convert to Item objects with scores
    items_with_scores = []
    for row in rows:
        item = await session.get(Item, row.id)
        if item:
            items_with_scores.append((item, row.similarity))

    return items_with_scores


async def batch_embed_items(
    session: AsyncSession,
    item_ids: list[UUID],
) -> int:
    """
    Batch embed multiple items.

    Args:
        session: Database session
        item_ids: List of item UUIDs to embed

    Returns:
        Number of items successfully embedded
    """
    count = 0
    for item_id in item_ids:
        try:
            await embed_item(session, item_id)
            count += 1
        except Exception:
            # Log error but continue
            pass
    return count
