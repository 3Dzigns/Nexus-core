"""Feedback scoring and ranking adjustment helpers."""

from typing import Iterable

from nexus_core.config import get_settings
from nexus_core.query.retrieval.reranker import RankedResult


def clamp_score(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Clamp a score to a bounded range."""
    return max(min_value, min(max_value, value))


def apply_feedback_adjustment(
    results: Iterable[RankedResult], weight: float | None = None
) -> None:
    """Apply feedback score adjustment to ranked results in place."""
    settings = get_settings()
    adjustment_weight = weight if weight is not None else settings.feedback_score_weight

    for result in results:
        if result.system_id is None:
            continue
        if result.feedback_score is None:
            continue

        adjusted = result.combined_score + (adjustment_weight * result.feedback_score)
        result.combined_score = clamp_score(adjusted)
