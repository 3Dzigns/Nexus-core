"""Query API endpoint.

POST /query - Execute knowledge queries with JWT authentication.

Reference: OPENAPI_v1.0.md POST /query, Phase 6.9
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.db.session import get_async_session
from nexus_core.query.auth.dependencies import get_current_user
from nexus_core.query.orchestrator import QueryOrchestrator
from nexus_core.query.schemas import JWTClaims, QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    user: Annotated[JWTClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> QueryResponse:
    """Execute knowledge query with JWT authentication.

    Security:
    - Requires valid JWT token (Bearer auth)
    - Role-based access control enforced
    - Scope restrictions applied (game/user context)
    - GM-only sources require ownership verification

    Classification:
    - DIRECT: No sources or direct commands
    - RETRIEVAL: Single/few chunks, no synthesis
    - SYNTHESIS: Multiple chunks requiring AI synthesis

    Args:
        request: Query request with query_text
        user: Validated JWT claims (from dependency)
        db: Database session (from dependency)

    Returns:
        Query response with text and source citations

    Raises:
        HTTPException: 400 if query invalid, 500 if processing fails
    """
    logger.info(
        f"Query request (user: {user.sub}, role: {user.role}, "
        f"game: {user.active_game_id}, query: {request.query_text[:100]})"
    )

    try:
        # Initialize orchestrator
        orchestrator = QueryOrchestrator(db)

        # Execute query
        response = await orchestrator.execute(
            query_text=request.query_text,
            user_id=user.sub,
            role=user.role,
            game_id=user.active_game_id,
            games_owned=user.games_owned,
        )

        logger.info(
            f"Query complete (user: {user.sub}, classification: {response.classification}, "
            f"sources: {len(response.sources)})"
        )

        return response

    except ValueError as e:
        logger.warning(f"Invalid query request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid query: {e}",
        )

    except Exception as e:
        logger.error(f"Query execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query execution failed. Please try again.",
        )
