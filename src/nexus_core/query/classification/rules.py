"""Deterministic short-circuit rules for query routing.

Rules applied in order per QUERY_POLICY_v1.0.md Section 3.2:
0. Scope validation (prerequisite)
1. No-scope rule: No sources → friendly message
2. Direct command rule: "list sources" → execute locally
3. Single-chunk rule: High confidence match → return chunk

Reference: QUERY_POLICY_v1.0.md Section 3.2, FR-028
"""

import logging
from enum import Enum
from typing import Optional

from nexus_core.query.classification.complexity import QueryComplexity
from nexus_core.query.schemas import QueryClassification
from nexus_core.query.scope.enforcer import ScopeEnforcementResult

logger = logging.getLogger(__name__)


class RulePath(str, Enum):
    """Short-circuit rule paths."""

    RULE_0_SCOPE_VALIDATION = "RULE_0_SCOPE_VALIDATION"
    RULE_1_NO_SOURCES = "RULE_1_NO_SOURCES"
    RULE_2_DIRECT_COMMAND = "RULE_2_DIRECT_COMMAND"
    RULE_3_SINGLE_CHUNK = "RULE_3_SINGLE_CHUNK"
    RULE_4_MULTI_CHUNK = "RULE_4_MULTI_CHUNK"
    NO_RULE_MATCH = "NO_RULE_MATCH"


class RuleResult:
    """Result of rule evaluation."""

    def __init__(
        self,
        matched: bool,
        rule_path: RulePath,
        classification: Optional[QueryClassification] = None,
        reason: Optional[str] = None,
    ):
        """Initialize rule result.

        Args:
            matched: Whether rule matched
            rule_path: Which rule was evaluated
            classification: Query classification if rule matched
            reason: Human-readable reason for match
        """
        self.matched = matched
        self.rule_path = rule_path
        self.classification = classification
        self.reason = reason

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"RuleResult(matched={self.matched}, rule={self.rule_path.value}, "
            f"classification={self.classification}, reason={self.reason})"
        )


class ShortCircuitRules:
    """Deterministic rules for query routing.

    Rules are evaluated in strict order. First match wins.
    """

    @staticmethod
    def rule_1_no_sources(enforcement: ScopeEnforcementResult) -> RuleResult:
        """Rule 1: No sources available → friendly message.

        Args:
            enforcement: Scope enforcement result

        Returns:
            Rule result (matched if no sources)
        """
        if not enforcement.has_sources:
            logger.info("Rule 1 matched: No sources available")
            return RuleResult(
                matched=True,
                rule_path=RulePath.RULE_1_NO_SOURCES,
                classification=QueryClassification.DIRECT,
                reason="No authoritative sources available in scope",
            )

        return RuleResult(
            matched=False,
            rule_path=RulePath.RULE_1_NO_SOURCES,
        )

    @staticmethod
    def rule_2_direct_command(
        query_text: str, complexity: QueryComplexity
    ) -> RuleResult:
        """Rule 2: Direct command → execute locally.

        Commands:
        - "list sources"
        - "show sources"
        - "what sources are available"

        Args:
            query_text: Query text
            complexity: Query complexity metrics

        Returns:
            Rule result (matched if direct command)
        """
        if complexity.has_command:
            text_lower = query_text.lower()

            # Check for source listing commands
            if any(
                phrase in text_lower
                for phrase in [
                    "list sources",
                    "show sources",
                    "what sources",
                    "which sources",
                    "available sources",
                ]
            ):
                logger.info("Rule 2 matched: Direct command (list sources)")
                return RuleResult(
                    matched=True,
                    rule_path=RulePath.RULE_2_DIRECT_COMMAND,
                    classification=QueryClassification.DIRECT,
                    reason="Direct command: list sources",
                )

        return RuleResult(
            matched=False,
            rule_path=RulePath.RULE_2_DIRECT_COMMAND,
        )

    @staticmethod
    def rule_3_single_chunk(
        retrieval_results: Optional[list] = None,
        confidence_threshold: float = 0.9,
    ) -> RuleResult:
        """Rule 3: Single high-confidence chunk → return without AI.

        Args:
            retrieval_results: Retrieved chunks with similarity scores
            confidence_threshold: Minimum similarity for single-chunk return

        Returns:
            Rule result (matched if single high-confidence chunk)
        """
        if not retrieval_results:
            return RuleResult(
                matched=False,
                rule_path=RulePath.RULE_3_SINGLE_CHUNK,
            )

        if len(retrieval_results) == 1:
            chunk, similarity = retrieval_results[0]
            if similarity >= confidence_threshold:
                logger.info(
                    f"Rule 3 matched: Single high-confidence chunk (similarity={similarity:.2f})"
                )
                return RuleResult(
                    matched=True,
                    rule_path=RulePath.RULE_3_SINGLE_CHUNK,
                    classification=QueryClassification.RETRIEVAL,
                    reason=f"Single chunk with high confidence ({similarity:.2f})",
                )

        return RuleResult(
            matched=False,
            rule_path=RulePath.RULE_3_SINGLE_CHUNK,
        )

    @staticmethod
    def rule_4_multi_chunk(retrieval_results: Optional[list] = None) -> RuleResult:
        """Rule 4: Multiple chunks → synthesis required.

        Args:
            retrieval_results: Retrieved chunks

        Returns:
            Rule result (matched if multiple chunks)
        """
        if retrieval_results and len(retrieval_results) > 1:
            logger.info(f"Rule 4 matched: Multiple chunks ({len(retrieval_results)})")
            return RuleResult(
                matched=True,
                rule_path=RulePath.RULE_4_MULTI_CHUNK,
                classification=QueryClassification.SYNTHESIS,
                reason=f"Multiple chunks require synthesis ({len(retrieval_results)} results)",
            )

        return RuleResult(
            matched=False,
            rule_path=RulePath.RULE_4_MULTI_CHUNK,
        )
