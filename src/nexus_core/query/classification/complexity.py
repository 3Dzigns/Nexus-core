"""Query complexity analysis.

Analyzes query characteristics to inform classification.

Reference: QUERY_POLICY_v1.0.md Section 3.1
"""

import logging
import re

logger = logging.getLogger(__name__)


class QueryComplexity:
    """Query complexity metrics."""

    def __init__(
        self,
        token_count: int,
        has_question: bool,
        has_command: bool,
        word_count: int,
    ):
        """Initialize complexity metrics.

        Args:
            token_count: Approximate token count
            has_question: Whether query contains question words
            has_command: Whether query is a command (list, show, etc.)
            word_count: Word count
        """
        self.token_count = token_count
        self.has_question = has_question
        self.has_command = has_command
        self.word_count = word_count

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"QueryComplexity(tokens={self.token_count}, "
            f"words={self.word_count}, question={self.has_question}, "
            f"command={self.has_command})"
        )


class ComplexityAnalyzer:
    """Analyzes query text to determine complexity metrics."""

    # Command keywords for direct routing
    COMMAND_KEYWORDS = {
        "list",
        "show",
        "display",
        "what sources",
        "which sources",
        "available sources",
    }

    # Question words for identifying questions
    QUESTION_WORDS = {
        "what",
        "who",
        "where",
        "when",
        "why",
        "how",
        "which",
        "can",
        "does",
        "is",
        "are",
    }

    @staticmethod
    def analyze(query_text: str) -> QueryComplexity:
        """Analyze query complexity.

        Args:
            query_text: Query text

        Returns:
            Complexity metrics
        """
        text_lower = query_text.lower().strip()

        # Word and token count (approximate)
        words = text_lower.split()
        word_count = len(words)
        # Rough token estimate: 1.3 tokens per word
        token_count = int(word_count * 1.3)

        # Check for questions
        has_question = any(
            word in text_lower.split()[:5]  # Check first 5 words
            for word in ComplexityAnalyzer.QUESTION_WORDS
        ) or text_lower.endswith("?")

        # Check for commands
        has_command = any(
            keyword in text_lower for keyword in ComplexityAnalyzer.COMMAND_KEYWORDS
        )

        complexity = QueryComplexity(
            token_count=token_count,
            has_question=has_question,
            has_command=has_command,
            word_count=word_count,
        )

        logger.debug(f"Complexity analysis: {complexity}")

        return complexity
