"""Database session management for Nexus Core."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from nexus_core.config import get_settings
from nexus_core.models.base import Base

settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Yields:
        AsyncSession: Database session for async operations.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session as a context manager.

    This function provides a session with automatic transaction management:
    - Commits on successful completion
    - Rolls back on exceptions
    - Ensures proper session cleanup

    Usage:
        async with get_async_session_context() as session:
            # Perform database operations
            result = await session.execute(query)
            # Automatically commits if no exceptions

    Yields:
        AsyncSession: Database session for async operations.

    Raises:
        Exception: Re-raises any exception after rolling back the transaction.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables.

    Note: In production, use Alembic migrations instead.
    This function is for development/testing convenience.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
