"""Feedback API endpoint.

POST /feedback - Submit thumbs-up/down feedback for a response.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.db.session import get_async_session
from nexus_core.feedback.schemas import FeedbackRequest, FeedbackResponse
from nexus_core.feedback.service import FeedbackError, record_feedback
from nexus_core.query.auth.dependencies import get_current_user
from nexus_core.query.schemas import JWTClaims

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    user: Annotated[JWTClaims, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> FeedbackResponse:
    """Submit feedback for a response chunk."""
    logger.info(
        "Feedback request (user=%s, doc_id=%s, chunk_id=%s, rating=%s)",
        user.sub,
        request.doc_id,
        request.chunk_id,
        request.rating,
    )

    try:
        response = await record_feedback(db, user, request)
        await db.commit()
        return response
    except FeedbackError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error("Feedback submission failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feedback submission failed. Please try again.",
        ) from e
