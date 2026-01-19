"""Schemas for feedback API requests and responses."""

from pydantic import BaseModel, Field

from nexus_core.models.source import FeedbackRating


class FeedbackRequest(BaseModel):
    """Feedback submission request."""

    doc_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
    rating: FeedbackRating


class FeedbackResponse(BaseModel):
    """Feedback submission response."""

    status: str = "accepted"
