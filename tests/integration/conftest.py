"""Integration test fixtures for dual-backend testing"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from kiroku_memory.db.config import settings
from kiroku_memory.db.models import Base


@pytest.fixture(params=["postgres", "surrealdb"])
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

        # Use temporary directory (each test gets clean slate)
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
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            pytest.skip("DATABASE_URL not configured")

        from kiroku_memory.db.repositories.postgres import PostgresUnitOfWork

        settings.backend = "postgres"

        # Create fresh engine for each test
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=1,
            max_overflow=0,
        )

        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Initialize tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create session for this test
        async with session_factory() as session:
            uow = PostgresUnitOfWork(session)
            yield uow
            await session.rollback()

        # Dispose engine to release connections
        await engine.dispose()

    settings.backend = original_backend
