"""Repository factory for backend selection"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from ..config import settings
from .base import UnitOfWork


@asynccontextmanager
async def get_unit_of_work() -> AsyncGenerator[UnitOfWork, None]:
    """
    Get a Unit of Work based on configured backend.

    Usage:
        async with get_unit_of_work() as uow:
            resource = await uow.resources.get(id)
            await uow.commit()
    """
    backend = getattr(settings, "backend", "postgres")

    if backend == "surrealdb":
        # SurrealDB implementation
        from ..surrealdb import get_surreal_connection
        from .surrealdb import SurrealUnitOfWork

        async with get_surreal_connection() as client:
            uow = SurrealUnitOfWork(client)
            try:
                yield uow
                await uow.commit()
            except Exception:
                await uow.rollback()
                raise
    else:
        # PostgreSQL (default)
        from ..database import async_session_factory
        from .postgres import PostgresUnitOfWork

        async with async_session_factory() as session:
            uow = PostgresUnitOfWork(session)
            try:
                yield uow
                await uow.commit()
            except Exception:
                await uow.rollback()
                raise
