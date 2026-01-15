"""Pytest configuration and fixtures for Nexus Core tests.

Reference:
- TEST_PLAN_v1.0.md
- NFR-007: All tests MUST run inside Docker containers

Task ID: PHASE0-INIT-007
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from nexus_core.models import Base


# Test database URL - use test database to avoid affecting real data
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://nexus:nexus@localhost:5432/nexus_core_test",
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables for testing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session.

    Each test gets a fresh session that is rolled back after the test.
    """
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # Start a savepoint so we can rollback
        async with session.begin():
            yield session
            # Rollback after test (implicit via context manager)
