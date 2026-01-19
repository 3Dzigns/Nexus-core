"""Query classification orchestrator.

Classifies queries as DIRECT, RETRIEVAL, or SYNTHESIS using deterministic rules.

Reference: QUERY_POLICY_v1.0.md Section 3, FR-027
"""

import logging
from typing import Optional

from nexus_core.query.classification.complexity import ComplexityAnalyzer, QueryComplexity
from nexus_core.query.classification.rules import RulePath, RuleResult, ShortCircuitRules
from nexus_core.query.schemas import QueryClassification
from nexus_core.query.scope.enforcer import ScopeEnforcementResult

logger = logging.getLogger(__name__)


class ClassificationResult:
    """Result of query classification."""

    def __init__(
        self,
        classification: QueryClassification,
        rule_path: RulePath,
        complexity: QueryComplexity,
        enforcement: ScopeEnforcementResult,
        reason: str,
    ):
        """Initialize classification result.

        Args:
            classification: Query classification level
            rule_path: Which rule determined classification
            complexity: Query complexity metrics
            enforcement: Scope enforcement result
            reason: Human-readable reason for classification
        """
        self.classification = classification
        self.rule_path = rule_path
        self.complexity = complexity
        self.enforcement = enforcement
        self.reason = reason

    def __repr__(self) -> str:
        """String representation for logging."""
        return (
            f"ClassificationResult(classification={self.classification}, "
            f"rule={self.rule_path.value}, reason={self.reason})"
        )


class QueryClassifier:
    """Classifies queries using deterministic rules.

    Classification Levels:
    - DIRECT: Deterministic or trivial lookup (no AI)
    - RETRIEVAL: Requires retrieval, no synthesis
    - SYNTHESIS: Requires AI synthesis

    Rules Applied in Order:
    1. No sources → DIRECT (friendly message)
    2. Direct command → DIRECT (local execution)
    3. Single high-confidence chunk → RETRIEVAL
    4. Multiple chunks → SYNTHESIS

    Reference: QUERY_POLICY_v1.0.md Section 3
    """

    def __init__(self):
        """Initialize query classifier."""
        self.rules = ShortCircuitRules()
        self.complexity_analyzer = ComplexityAnalyzer()

    async def classify(
        self,
        query_text: str,
        enforcement: ScopeEnforcementResult,
        retrieval_results: Optional[list] = None,
    ) -> ClassificationResult:
        """Classify query using deterministic rules.

        Args:
            query_text: Query text
            enforcement: Scope enforcement result
            retrieval_results: Optional retrieval results (for Rule 3/4)

        Returns:
            Classification result
        """
        logger.info(f"Classifying query: {query_text[:100]}...")

        # Analyze complexity
        complexity = self.complexity_analyzer.analyze(query_text)

        # Rule 1: No sources
        rule_result = self.rules.rule_1_no_sources(enforcement)
        if rule_result.matched:
            return self._build_result(rule_result, complexity, enforcement)

        # Rule 2: Direct command
        rule_result = self.rules.rule_2_direct_command(query_text, complexity)
        if rule_result.matched:
            return self._build_result(rule_result, complexity, enforcement)

        # If retrieval results provided, check Rules 3 & 4
        if retrieval_results is not None:
            # Rule 3: Single high-confidence chunk
            rule_result = self.rules.rule_3_single_chunk(retrieval_results)
            if rule_result.matched:
                return self._build_result(rule_result, complexity, enforcement)

            # Rule 4: Multiple chunks
            rule_result = self.rules.rule_4_multi_chunk(retrieval_results)
            if rule_result.matched:
                return self._build_result(rule_result, complexity, enforcement)

        # Default: Classify based on complexity
        return self._classify_by_complexity(query_text, complexity, enforcement)

    def _build_result(
        self,
        rule_result: RuleResult,
        complexity: QueryComplexity,
        enforcement: ScopeEnforcementResult,
    ) -> ClassificationResult:
        """Build classification result from rule result.

        Args:
            rule_result: Rule evaluation result
            complexity: Query complexity
            enforcement: Scope enforcement

        Returns:
            Classification result
        """
        return ClassificationResult(
            classification=rule_result.classification,
            rule_path=rule_result.rule_path,
            complexity=complexity,
            enforcement=enforcement,
            reason=rule_result.reason,
        )

    def _classify_by_complexity(
        self,
        query_text: str,
        complexity: QueryComplexity,
        enforcement: ScopeEnforcementResult,
    ) -> ClassificationResult:
        """Fallback classification based on complexity.

        Used when no rules match (requires retrieval).

        Args:
            query_text: Query text
            complexity: Query complexity
            enforcement: Scope enforcement

        Returns:
            Classification result
        """
        # Default: RETRIEVAL (will run retrieval, then reclassify)
        classification = QueryClassification.RETRIEVAL

        reason = "No rule match, requires retrieval"

        logger.info(
            f"No rule matched, defaulting to {classification} "
            f"(complexity: {complexity.token_count} tokens)"
        )

        return ClassificationResult(
            classification=classification,
            rule_path=RulePath.NO_RULE_MATCH,
            complexity=complexity,
            enforcement=enforcement,
            reason=reason,
        )
