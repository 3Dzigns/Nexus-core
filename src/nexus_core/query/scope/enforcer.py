"""Scope enforcement before retrieval.

Validates that scope is non-empty before proceeding with retrieval.
Implements fail-fast validation per QUERY_POLICY_v1.0.md Section 2.2.

Reference: QUERY_POLICY_v1.0.md Section 2.2, FR-028, FR-032, FR-033
"""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.models.source import Chunk, GovernanceStatus, Source
from nexus_core.query.auth.role_checker import RoleChecker
from nexus_core.query.schemas import Role
from nexus_core.query.scope.resolver import QueryScope
from nexus_core.query.scope.source_filter import SourceFilter

logger = logging.getLogger(__name__)


class ScopeEnforcementResult:
    """Result of scope enforcement validation."""

    def __init__(
        self,
        has_sources: bool,
        source_count: int,
        chunk_count: int,
        scope: QueryScope,
    ):
        """Initialize enforcement result.

        Args:
            has_sources: Whether any sources are accessible
            source_count: Number of accessible sources
            chunk_count: Number of accessible chunks
            scope: The query scope that was validated
        """
        self.has_sources = has_sources
        self.source_count = source_count
        self.chunk_count = chunk_count
        self.scope = scope

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"ScopeEnforcementResult(has_sources={self.has_sources}, "
            f"sources={self.source_count}, chunks={self.chunk_count})"
        )


class ScopeEnforcer:
    """Enforces scope restrictions before retrieval.

    Fail-fast validation:
    - No sources → Short-circuit with friendly message
    - Empty scope → Early exit before retrieval
    """

    def __init__(self, db: AsyncSession):
        """Initialize scope enforcer.

        Args:
            db: Database session
        """
        self.db = db

    async def validate_scope(self, scope: QueryScope) -> ScopeEnforcementResult:
        """Validate that scope contains accessible sources.

        Performs fast count query to check if any sources are available
        before proceeding with expensive retrieval operations.

        Args:
            scope: Resolved query scope

        Returns:
            Enforcement result with source/chunk counts
        """
        logger.info(f"Validating scope: {scope}")

        # Build scope-filtered query
        query = SourceFilter.build_chunk_query(scope)

        # Count accessible sources and chunks
        source_count_query = (
            select(func.count(func.distinct(Source.doc_id)))
            .select_from(Source)
            .join(Chunk, Chunk.doc_id == Source.doc_id)
            .where(
                Source.status == GovernanceStatus.INGESTED,
                Chunk.active == True,  # noqa: E712
            )
        )

        # Apply scope filters to source count
        if scope.is_game_context:
            source_count_query = source_count_query.where(Source.game_id == scope.game_id)
        else:
            source_count_query = source_count_query.where(
                Source.owner_user_id == scope.user_id
            )

        # Execute count query
        result = await self.db.execute(source_count_query)
        source_count = result.scalar() or 0

        # Count chunks
        chunk_count_query = (
            select(func.count(Chunk.chunk_id))
            .select_from(Chunk)
            .join(Source, Chunk.doc_id == Source.doc_id)
            .where(
                Source.status == GovernanceStatus.INGESTED,
                Chunk.active == True,  # noqa: E712
            )
        )

        if scope.is_game_context:
            chunk_count_query = chunk_count_query.where(Source.game_id == scope.game_id)
        else:
            chunk_count_query = chunk_count_query.where(
                Source.owner_user_id == scope.user_id
            )

        result = await self.db.execute(chunk_count_query)
        chunk_count = result.scalar() or 0

        has_sources = source_count > 0

        enforcement_result = ScopeEnforcementResult(
            has_sources=has_sources,
            source_count=source_count,
            chunk_count=chunk_count,
            scope=scope,
        )

        logger.info(f"Scope validation complete: {enforcement_result}")

        return enforcement_result

    async def get_accessible_doc_ids(self, scope: QueryScope) -> list[str]:
        """Get list of accessible doc_ids for the given scope.

        Args:
            scope: Resolved query scope

        Returns:
            List of accessible doc_ids (empty if none available)
        """
        query = SourceFilter.build_source_list_query(scope)

        result = await self.db.execute(query)
        sources = result.scalars().all()

        doc_ids = [source.doc_id for source in sources]

        logger.debug(f"Found {len(doc_ids)} accessible sources for scope: {scope}")

        return doc_ids
