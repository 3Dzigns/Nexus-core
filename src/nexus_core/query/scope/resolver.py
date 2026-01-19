"""Scope resolution from JWT claims.

Determines query scope (game vs global context) from validated JWT.

Reference: QUERY_POLICY_v1.0.md Section 2, ACCESS_MATRIX_v1.0.md
"""

import logging
from typing import Optional

from nexus_core.query.schemas import JWTClaims, Role

logger = logging.getLogger(__name__)


class QueryScope:
    """Resolved query scope from JWT claims.

    Defines what sources are accessible for the query.
    """

    def __init__(
        self,
        user_id: str,
        role: Role,
        game_id: Optional[str] = None,
        games_owned: Optional[list[str]] = None,
    ):
        """Initialize query scope.

        Args:
            user_id: User UUID from JWT sub claim
            role: User role from JWT role claim
            game_id: Active game context from JWT (null = global scope)
            games_owned: Games owned by GM (empty for non-GM)
        """
        self.user_id = user_id
        self.role = role
        self.game_id = game_id
        self.games_owned = games_owned or []

    @property
    def is_game_context(self) -> bool:
        """Check if query is in game context."""
        return self.game_id is not None

    @property
    def is_global_context(self) -> bool:
        """Check if query is in global (user-only) context."""
        return self.game_id is None

    @property
    def is_gm_owned_game(self) -> bool:
        """Check if user is GM and owns the active game."""
        return (
            self.role == Role.GM
            and self.game_id is not None
            and self.game_id in self.games_owned
        )

    def __repr__(self) -> str:
        """String representation for logging."""
        context = f"game:{self.game_id}" if self.game_id else "global"
        return f"QueryScope(user={self.user_id}, role={self.role}, context={context})"


class ScopeResolver:
    """Resolves query scope from JWT claims.

    Extracts user_id, game_id, role from validated JWT.
    Never accepts scope information from client input.
    """

    @staticmethod
    def resolve(claims: JWTClaims) -> QueryScope:
        """Resolve query scope from JWT claims.

        Scope Rules (per QUERY_POLICY_v1.0.md Section 2.1):
        - Game context: Only sources linked to active_game_id
        - Global context: Only sources owned by user
        - Admin: Special audit-only mode (enforced during classification)

        Args:
            claims: Validated JWT claims

        Returns:
            Resolved query scope
        """
        scope = QueryScope(
            user_id=claims.sub,
            role=claims.role,
            game_id=claims.active_game_id,
            games_owned=claims.games_owned,
        )

        logger.info(f"Scope resolved: {scope}")

        return scope
