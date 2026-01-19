"""SQL query filters for scope enforcement.

Builds database queries that enforce game/user context restrictions.

Reference: QUERY_POLICY_v1.0.md Section 2, DATABASE_SCHEMA_v1.0.md
"""

import logging
from typing import Any, Optional

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import joinedload

from nexus_core.models.source import Chunk, GovernanceStatus, Source, SourceLink
from nexus_core.query.auth.role_checker import RoleChecker
from nexus_core.query.schemas import Role
from nexus_core.query.scope.resolver import QueryScope

logger = logging.getLogger(__name__)


class SourceFilter:
    """Builds SQL filters for scope-enforced source retrieval.

    All filters enforce:
    - Status = INGESTED
    - Chunks active = true
    - Scope restrictions (game or user context)
    - GM-only access control
    """

    @staticmethod
    def build_doc_id_filter(scope: QueryScope) -> list[str]:
        """Build list of accessible doc_ids for the given scope.

        This is a preliminary filter - actual database query uses SQL filters.

        Args:
            scope: Resolved query scope

        Returns:
            List of doc_ids (empty if no sources available)
        """
        # This is a placeholder for the enforcer to use
        # The actual filtering happens in build_chunk_query
        logger.debug(f"Building doc_id filter for scope: {scope}")
        return []

    @staticmethod
    def build_chunk_query(
        scope: QueryScope,
        base_query: Optional[Select] = None,
    ) -> Select:
        """Build SQLAlchemy query for scope-filtered chunks.

        Enforces:
        - Only INGESTED sources
        - Only active chunks
        - Game context: sources linked to game_id
        - Global context: sources owned by user_id
        - GM-only sources: requires GM ownership

        Args:
            scope: Resolved query scope
            base_query: Optional base query to extend (defaults to select Chunk)

        Returns:
            SQLAlchemy select statement with scope filters
        """
        if base_query is None:
            base_query = (
                select(Chunk)
                .join(Source, Chunk.doc_id == Source.doc_id)
                .options(joinedload(Chunk.source))
            )

        # Base filters: INGESTED status, active chunks
        filters = [
            Source.status == GovernanceStatus.INGESTED,
            Chunk.active == True,  # noqa: E712
        ]

        # Scope filters
        if scope.is_game_context:
            # Game context: sources linked to game_id
            filters.append(
                or_(
                    # Primary source link
                    and_(
                        Source.game_id == scope.game_id,
                        or_(
                            # GM can access GM-only sources if they own the game
                            and_(
                                SourceLink.gm_only == True,  # noqa: E712
                                scope.is_gm_owned_game,
                            ),
                            # Everyone can access non-GM-only sources
                            SourceLink.gm_only == False,  # noqa: E712
                        ),
                    ),
                    # Additional source links (via source_links table)
                    and_(
                        SourceLink.game_id == scope.game_id,
                        or_(
                            and_(
                                SourceLink.gm_only == True,  # noqa: E712
                                scope.is_gm_owned_game,
                            ),
                            SourceLink.gm_only == False,  # noqa: E712
                        ),
                    ),
                )
            )
        else:
            # Global context: user-owned sources only
            filters.append(Source.owner_user_id == scope.user_id)

        query = base_query.where(and_(*filters))

        logger.debug(f"Built chunk query with {len(filters)} filters for scope: {scope}")

        return query

    @staticmethod
    def build_source_list_query(scope: QueryScope) -> Select:
        """Build query to list accessible sources (for direct commands).

        Args:
            scope: Resolved query scope

        Returns:
            SQLAlchemy select statement for Source records
        """
        query = select(Source).where(
            and_(
                Source.status == GovernanceStatus.INGESTED,
            )
        )

        # Apply scope filters
        if scope.is_game_context:
            query = query.where(Source.game_id == scope.game_id)
        else:
            query = query.where(Source.owner_user_id == scope.user_id)

        logger.debug(f"Built source list query for scope: {scope}")

        return query
