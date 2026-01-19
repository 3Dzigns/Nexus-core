"""Feedback persistence and admin flagging logic."""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import get_settings
from nexus_core.feedback.schemas import FeedbackRequest, FeedbackResponse
from nexus_core.models.source import (
    Chunk,
    EventType,
    Feedback,
    FeedbackRating,
    GovernanceEvent,
)
from nexus_core.query.schemas import JWTClaims

logger = logging.getLogger(__name__)


class FeedbackError(Exception):
    """Raised when feedback submission fails validation."""

    pass


async def record_feedback(
    session: AsyncSession,
    user: JWTClaims,
    request: FeedbackRequest,
) -> FeedbackResponse:
    """Record feedback and update ranking score."""
    chunk = await _get_chunk(session, request.doc_id, request.chunk_id)

    feedback = Feedback(
        doc_id=request.doc_id,
        chunk_id=request.chunk_id,
        rating=request.rating,
        user_id=user.sub,
    )
    session.add(feedback)

    await session.flush()

    score, up_votes, down_votes = await _recalculate_score(session, request.chunk_id)
    chunk.feedback_score = score

    if down_votes >= get_settings().feedback_negative_threshold:
        await _flag_for_admin_review(
            session,
            doc_id=request.doc_id,
            chunk_id=request.chunk_id,
            user_id=user.sub,
            score=score,
            down_votes=down_votes,
        )

    logger.info(
        "Feedback recorded (user=%s, doc_id=%s, chunk_id=%s, rating=%s, score=%s)",
        user.sub,
        request.doc_id,
        request.chunk_id,
        request.rating,
        score,
    )

    return FeedbackResponse()


async def _get_chunk(
    session: AsyncSession, doc_id: str, chunk_id: str
) -> Chunk:
    """Fetch chunk for feedback validation."""
    result = await session.execute(
        select(Chunk).where(Chunk.doc_id == doc_id, Chunk.chunk_id == chunk_id)
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise FeedbackError("Chunk not found for given doc_id.")
    return chunk


async def _recalculate_score(
    session: AsyncSession, chunk_id: str
) -> tuple[int, int, int]:
    """Recalculate feedback score for a chunk."""
    up_votes = await _count_feedback(session, chunk_id, FeedbackRating.UP)
    down_votes = await _count_feedback(session, chunk_id, FeedbackRating.DOWN)

    score = up_votes - down_votes
    score = max(-10, min(10, score))

    return score, up_votes, down_votes


async def _count_feedback(
    session: AsyncSession, chunk_id: str, rating: FeedbackRating
) -> int:
    """Count feedback records for a chunk by rating."""
    result = await session.execute(
        select(func.count(Feedback.feedback_id)).where(
            Feedback.chunk_id == chunk_id,
            Feedback.rating == rating,
        )
    )
    return int(result.scalar() or 0)


async def _flag_for_admin_review(
    session: AsyncSession,
    doc_id: str,
    chunk_id: str,
    user_id: str,
    score: int,
    down_votes: int,
) -> None:
    """Create a governance event to flag content for admin review."""
    existing = await session.execute(
        select(GovernanceEvent).where(
            GovernanceEvent.doc_id == doc_id,
            GovernanceEvent.event_type == EventType.STATUS_CHANGE,
            GovernanceEvent.to_status == "FEEDBACK_FLAG",
            GovernanceEvent.metadata_json["chunk_id"].astext == chunk_id,
        )
    )
    if existing.scalar_one_or_none():
        return

    event = GovernanceEvent(
        doc_id=doc_id,
        from_status=None,
        to_status="FEEDBACK_FLAG",
        event_type=EventType.STATUS_CHANGE,
        triggered_by=user_id,
        metadata_json={
            "feedback_flag": True,
            "chunk_id": chunk_id,
            "score": score,
            "down_votes": down_votes,
        },
    )
    session.add(event)
