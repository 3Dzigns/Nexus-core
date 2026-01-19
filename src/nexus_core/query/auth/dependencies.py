"""FastAPI dependency injection for authentication.

Security Requirements:
- Per-route dependency injection (no global middleware)
- JWT validation on protected endpoints
- Role validation
- Never trust client-provided claims

Reference: JWT_SPEC_v1.0.md, OPENAPI_v1.0.md
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from nexus_core.query.auth.jwt_validator import JWTValidationError, JWTValidator
from nexus_core.query.auth.role_checker import RoleChecker, RoleViolationError
from nexus_core.query.schemas import JWTClaims, Role

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for JWT tokens
security = HTTPBearer()


def get_jwt_validator() -> JWTValidator:
    """Get JWT validator instance.

    Returns:
        Configured JWT validator
    """
    return JWTValidator()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    validator: Annotated[JWTValidator, Depends(get_jwt_validator)],
) -> JWTClaims:
    """Extract and validate JWT claims from request.

    FastAPI dependency for protected endpoints.

    Args:
        credentials: HTTP Bearer credentials
        validator: JWT validator instance

    Returns:
        Validated JWT claims

    Raises:
        HTTPException: 401 if token invalid, 403 if unauthorized
    """
    token = credentials.credentials

    try:
        claims = validator.validate_token(token)

        # Verify user can execute queries
        RoleChecker.check_query_access(claims)

        logger.info(
            f"User authenticated (user: {claims.sub}, role: {claims.role}, "
            f"game: {claims.active_game_id})"
        )

        return claims

    except JWTValidationError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except RoleViolationError as e:
        logger.warning(f"Authorization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions: {e}",
        )


async def get_admin_user(
    claims: Annotated[JWTClaims, Depends(get_current_user)],
) -> JWTClaims:
    """Verify current user has admin role.

    FastAPI dependency for admin-only endpoints.

    Args:
        claims: Validated JWT claims

    Returns:
        Validated admin JWT claims

    Raises:
        HTTPException: 403 if not admin
    """
    try:
        RoleChecker.check_admin_only(claims)
        return claims

    except RoleViolationError as e:
        logger.warning(f"Admin access denied (user: {claims.sub}): {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


async def get_gm_user(
    claims: Annotated[JWTClaims, Depends(get_current_user)],
) -> JWTClaims:
    """Verify current user has GM role.

    FastAPI dependency for GM-only endpoints.

    Args:
        claims: Validated JWT claims

    Returns:
        Validated GM JWT claims

    Raises:
        HTTPException: 403 if not GM
    """
    if claims.role != Role.GM:
        logger.warning(f"GM access denied (user: {claims.sub}, role: {claims.role})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GM access required",
        )

    return claims
