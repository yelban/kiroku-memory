"""PostgreSQL Unit of Work implementation"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..base import UnitOfWork
from .resource import PostgresResourceRepository
from .item import PostgresItemRepository
from .category import PostgresCategoryRepository
from .graph import PostgresGraphRepository
from .embedding import PostgresEmbeddingRepository
from .category_access import PostgresCategoryAccessRepository


class PostgresUnitOfWork(UnitOfWork):
    """PostgreSQL implementation of Unit of Work pattern"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self.resources = PostgresResourceRepository(session)
        self.items = PostgresItemRepository(session)
        self.categories = PostgresCategoryRepository(session)
        self.graph = PostgresGraphRepository(session)
        self.embeddings = PostgresEmbeddingRepository(session)
        self.category_accesses = PostgresCategoryAccessRepository(session)

    async def __aenter__(self) -> "PostgresUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
        # Note: commit is NOT automatic - caller must explicitly commit

    async def commit(self) -> None:
        """Commit the transaction"""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the transaction"""
        await self._session.rollback()
