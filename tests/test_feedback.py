"""Tests for feedback collection and ranking adjustments."""

import pytest
from sqlalchemy import select

from nexus_core.feedback.schemas import FeedbackRequest
from nexus_core.feedback.scoring import apply_feedback_adjustment
from nexus_core.feedback.service import record_feedback
from nexus_core.models.source import (
    Chunk,
    FeedbackRating,
    GovernanceEvent,
    GovernanceStatus,
    Source,
    ToolId,
)
from nexus_core.query.retrieval.reranker import RankedResult
from nexus_core.query.schemas import JWTClaims, Role


@pytest.mark.asyncio
async def test_feedback_score_and_flagging(session):
    source = Source(
        doc_id="test_doc__abc123",
        source_sha256="abc123",
        original_filename="test_doc.pdf",
        current_path="/transfer_station/sources/test_doc.pdf",
        status=GovernanceStatus.INGESTED,
        owner_user_id="user-1",
        system_id="sys-1",
    )
    chunk = Chunk(
        chunk_id="chunk-1",
        doc_id=source.doc_id,
        tool_id=ToolId.DOCLING,
        chunk_text="Some rules text.",
        chunk_sha256="chunksha",
        chunk_index=0,
        system_id="sys-1",
        feedback_score=0.0,
    )
    session.add_all([source, chunk])
    await session.flush()

    claims = JWTClaims(
        sub="user-1",
        role=Role.PLAYER,
        active_game_id=None,
        games_owned=[],
        tier="FREE",
        exp=0,
        iss="nexus-core-api",
    )

    request = FeedbackRequest(
        doc_id=source.doc_id,
        chunk_id=chunk.chunk_id,
        rating=FeedbackRating.DOWN,
    )

    for _ in range(10):
        await record_feedback(session, claims, request)

    await session.refresh(chunk)
    assert chunk.feedback_score == -10

    event = await session.execute(
        select(GovernanceEvent).where(
            GovernanceEvent.doc_id == source.doc_id,
            GovernanceEvent.to_status == "FEEDBACK_FLAG",
        )
    )
    assert event.scalar_one_or_none() is not None


def test_feedback_adjustment_lowers_rank():
    result = RankedResult(
        chunk_id="chunk-1",
        doc_id="doc-1",
        tool_id="docling",
        chunk_text="text",
        combined_score=0.5,
        system_id="sys-1",
        feedback_score=-10,
        keyword_score=0.5,
        vector_score=None,
    )

    apply_feedback_adjustment([result], weight=0.02)

    assert result.combined_score < 0.5
