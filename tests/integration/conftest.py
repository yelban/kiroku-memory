"""Integration test fixtures for dual-backend testing"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from kiroku_memory.db.config import settings


@pytest.fixture(params=["surrealdb"])  # Add "postgres" when DB is available
def backend(request):
    """Parameterized fixture for testing both backends"""
    return request.param


@pytest_asyncio.fixture
async def unit_of_work(backend) -> AsyncGenerator:
    """Get a Unit of Work for the specified backend"""
    original_backend = settings.backend

    if backend == "surrealdb":
        # Skip if surrealdb not installed
        pytest.importorskip("surrealdb")

        from surrealdb import AsyncSurreal
        from kiroku_memory.db.repositories.surrealdb import SurrealUnitOfWork

        # Use temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            url = f"file://{tmpdir}/test"

            client = AsyncSurreal(url)
            await client.connect()
            await client.use("test", "test")

            # Initialize schema
            schema_path = Path(__file__).parent.parent.parent / "kiroku_memory" / "db" / "surrealdb" / "schema.surql"
            if schema_path.exists():
                schema_sql = schema_path.read_text()
                await client.query(schema_sql)

            uow = SurrealUnitOfWork(client)
            yield uow

            await client.close()

    elif backend == "postgres":
        # Skip if no database URL configured
        if not os.environ.get("DATABASE_URL"):
            pytest.skip("DATABASE_URL not configured")

        from kiroku_memory.db.database import async_session_factory, init_db
        from kiroku_memory.db.repositories.postgres import PostgresUnitOfWork

        settings.backend = "postgres"
        await init_db()

        async with async_session_factory() as session:
            uow = PostgresUnitOfWork(session)
            yield uow
            await session.rollback()  # Don't persist test data

    settings.backend = original_backend
