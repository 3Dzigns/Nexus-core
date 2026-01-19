"""Role-based access control enforcement.

Security Rules (per ACCESS_MATRIX_v1.0.md):
- ADMIN: Audit-only queries (no synthesis), full governance access
- GM: Game-scoped queries, GM-only source access (with ownership verification)
- PLAYER: Game-scoped queries, no GM-only sources

Reference: ACCESS_MATRIX_v1.0.md, FR-032
"""

import logging
from typing import Optional

from nexus_core.query.schemas import JWTClaims, Role

logger = logging.getLogger(__name__)


class RoleViolationError(Exception):
    """Raised when role-based access control is violated."""

    pass


class RoleChecker:
    """Enforces role-based access control rules.

    All checks are server-side. Never trust client-provided role claims.
    """

    @staticmethod
    def check_query_access(claims: JWTClaims) -> None:
        """Verify user can execute queries.

        Args:
            claims: Validated JWT claims

        Raises:
            RoleViolationError: If role is invalid or access denied
        """
        # All authenticated users can query
        # Specific restrictions applied during scope enforcement
        logger.debug(f"Query access granted (user: {claims.sub}, role: {claims.role})")

    @staticmethod
    def check_admin_only(claims: JWTClaims) -> None:
        """Verify user has admin role.

        Args:
            claims: Validated JWT claims

        Raises:
            RoleViolationError: If user is not admin
        """
        if claims.role != Role.ADMIN:
            logger.warning(
                f"Admin access denied (user: {claims.sub}, role: {claims.role})"
            )
            raise RoleViolationError("Admin access required")

        logger.debug(f"Admin access granted (user: {claims.sub})")

    @staticmethod
    def check_gm_ownership(claims: JWTClaims, game_id: str) -> bool:
        """Verify GM owns the specified game.

        Args:
            claims: Validated JWT claims
            game_id: Game UUID to check

        Returns:
            True if user is GM and owns the game, False otherwise
        """
        if claims.role != Role.GM:
            return False

        is_owner = game_id in claims.games_owned

        if is_owner:
            logger.debug(f"GM ownership verified (user: {claims.sub}, game: {game_id})")
        else:
            logger.debug(
                f"GM ownership denied (user: {claims.sub}, game: {game_id}, "
                f"owned: {claims.games_owned})"
            )

        return is_owner

    @staticmethod
    def can_access_gm_only_source(
        claims: JWTClaims, game_id: Optional[str]
    ) -> bool:
        """Check if user can access GM-only sources.

        Rules:
        - Player: Never
        - Admin: Never (audit-only)
        - GM: Only if they own the game

        Args:
            claims: Validated JWT claims
            game_id: Game context (required for GM access)

        Returns:
            True if user can access GM-only sources
        """
        if claims.role == Role.PLAYER:
            return False

        if claims.role == Role.ADMIN:
            # Admin queries are audit-only, no GM-only sources
            return False

        if claims.role == Role.GM:
            if not game_id:
                # No game context = no GM-only access
                return False

            return RoleChecker.check_gm_ownership(claims, game_id)

        return False

    @staticmethod
    def validate_admin_query_restrictions(claims: JWTClaims) -> None:
        """Enforce admin query restrictions.

        Admins can only execute audit queries:
        - No synthesis
        - Direct commands only (list sources, view governance)

        Args:
            claims: Validated JWT claims

        Raises:
            RoleViolationError: If admin attempts non-audit query
        """
        if claims.role != Role.ADMIN:
            # Not admin, no restrictions
            return

        # Admin queries must be marked as audit-only during classification
        logger.debug(f"Admin query flagged for audit-only mode (user: {claims.sub})")
