"""SurrealDB connection management for embedded mode (SurrealKV)"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator, Optional

if TYPE_CHECKING:
    from surrealdb import AsyncSurreal


class SurrealConnection:
    """
    SurrealDB connection wrapper for embedded mode.

    Uses SurrealKV as the storage engine for embedded file-based storage.
    Connection string format: file://./path/to/data
    """

    _instance: Optional["SurrealConnection"] = None
    _client: Optional["AsyncSurreal"] = None
    _initialized: bool = False

    def __init__(
        self,
        url: Optional[str] = None,
        namespace: Optional[str] = None,
        database: Optional[str] = None,
    ):
        from ..config import settings

        self.url = url or settings.surreal_url
        self.namespace = namespace or settings.surreal_namespace
        self.database = database or settings.surreal_database

        # Ensure data directory exists for file:// URLs
        if self.url.startswith("file://"):
            data_path = self.url.replace("file://", "")
            # Handle relative paths
            if data_path.startswith("./"):
                data_path = Path.cwd() / data_path[2:]
            else:
                data_path = Path(data_path)
            data_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> "SurrealConnection":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)"""
        cls._instance = None
        cls._client = None
        cls._initialized = False

    async def connect(self) -> "AsyncSurreal":
        """
        Connect to SurrealDB and return the client.

        Returns:
            AsyncSurreal client instance
        """
        if self._client is not None:
            return self._client

        from surrealdb import AsyncSurreal

        self._client = AsyncSurreal(self.url)
        await self._client.connect()
        await self._client.use(self.namespace, self.database)

        return self._client

    async def disconnect(self) -> None:
        """Disconnect from SurrealDB"""
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._initialized = False

    async def init_schema(self, force: bool = False) -> None:
        """
        Initialize database schema from schema.surql.

        Args:
            force: If True, reinitialize even if already done
        """
        if self._initialized and not force:
            return

        client = await self.connect()

        # Load schema file
        schema_path = Path(__file__).parent / "schema.surql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        schema_sql = schema_path.read_text()

        # Execute schema (SurrealDB handles idempotent DEFINE statements)
        await client.query(schema_sql)

        self._initialized = True

    @property
    def client(self) -> Optional["AsyncSurreal"]:
        """Get current client (may be None if not connected)"""
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._client is not None


@asynccontextmanager
async def get_surreal_connection() -> AsyncGenerator["AsyncSurreal", None]:
    """
    Async context manager for getting a SurrealDB connection.

    Usage:
        async with get_surreal_connection() as db:
            result = await db.query("SELECT * FROM item")

    Yields:
        AsyncSurreal client instance
    """
    conn = SurrealConnection.get_instance()
    client = await conn.connect()
    try:
        yield client
    finally:
        # Don't disconnect - maintain connection pool
        pass


async def init_surreal_db(force: bool = False) -> None:
    """
    Initialize SurrealDB with schema.

    Should be called at application startup.

    Args:
        force: If True, reinitialize schema even if already done
    """
    conn = SurrealConnection.get_instance()
    await conn.init_schema(force=force)


async def close_surreal_db() -> None:
    """
    Close SurrealDB connection.

    Should be called at application shutdown.
    """
    conn = SurrealConnection.get_instance()
    await conn.disconnect()
    SurrealConnection.reset_instance()
