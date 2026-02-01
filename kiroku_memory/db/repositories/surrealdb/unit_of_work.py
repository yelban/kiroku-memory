"""SurrealDB Unit of Work implementation"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import UnitOfWork
from .resource import SurrealResourceRepository
from .item import SurrealItemRepository
from .category import SurrealCategoryRepository
from .graph import SurrealGraphRepository
from .embedding import SurrealEmbeddingRepository
from .category_access import SurrealCategoryAccessRepository

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealUnitOfWork(UnitOfWork):
    """
    SurrealDB implementation of Unit of Work pattern.

    Note: SurrealDB transactions are different from traditional RDBMS.
    Each query is atomic by default. For multi-statement transactions,
    use BEGIN/COMMIT/CANCEL statements.
    """

    def __init__(self, client: "AsyncSurreal"):
        self._client = client
        self._in_transaction = False

        # Initialize repositories with shared client
        self.resources = SurrealResourceRepository(client)
        self.items = SurrealItemRepository(client)
        self.categories = SurrealCategoryRepository(client)
        self.graph = SurrealGraphRepository(client)
        self.embeddings = SurrealEmbeddingRepository(client)
        self.category_accesses = SurrealCategoryAccessRepository(client)

    async def __aenter__(self) -> "SurrealUnitOfWork":
        # Start transaction
        await self._client.query("BEGIN TRANSACTION")
        self._in_transaction = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
        # Note: commit is NOT automatic - caller must explicitly commit
        # If caller forgets, the transaction will be cancelled on disconnect

    async def commit(self) -> None:
        """Commit the transaction"""
        if self._in_transaction:
            await self._client.query("COMMIT TRANSACTION")
            self._in_transaction = False

    async def rollback(self) -> None:
        """Rollback the transaction"""
        if self._in_transaction:
            await self._client.query("CANCEL TRANSACTION")
            self._in_transaction = False
