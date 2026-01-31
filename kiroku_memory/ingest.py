"""Raw resource ingestion - append-only log storage"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db.models import Resource


async def ingest_message(
    session: AsyncSession,
    content: str,
    source: str,
    metadata: Optional[dict] = None,
) -> UUID:
    """
    Ingest a raw message into append-only resource log.

    Args:
        session: Database session
        content: Raw message content
        source: Source identifier (e.g., "user:123", "api:webhook")
        metadata: Optional metadata dict

    Returns:
        UUID of created resource
    """
    resource = Resource(
        content=content,
        source=source,
        metadata_=metadata or {},
    )
    session.add(resource)
    await session.flush()
    return resource.id


async def get_resource(session: AsyncSession, resource_id: UUID) -> Optional[Resource]:
    """Get resource by ID"""
    result = await session.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    return result.scalar_one_or_none()


async def list_resources(
    session: AsyncSession,
    source: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
) -> list[Resource]:
    """
    List resources with optional filters.

    Args:
        session: Database session
        source: Filter by source
        since: Only resources created after this time
        limit: Maximum number of results

    Returns:
        List of Resource objects
    """
    query = select(Resource).order_by(Resource.created_at.desc()).limit(limit)

    if source:
        query = query.where(Resource.source == source)
    if since:
        query = query.where(Resource.created_at > since)

    result = await session.execute(query)
    return list(result.scalars().all())
