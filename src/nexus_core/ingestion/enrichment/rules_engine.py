"""Enrichment rules engine for deterministic content classification.

Per INGESTION_ARCHITECTURE_v1.0.md Section 9.2:
- Load system-specific rules from YAML files
- Apply deterministic pattern matching (regex + keywords)
- NO per-chunk LLM calls in MVP1
- Record enrichment_rules_version in output

Requirements: FR-016, FR-017, FR-018
"""

import logging
import re
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class EnrichmentRulesEngine:
    """Engine for loading and applying enrichment rules.

    Rules are defined in YAML files per system:
    /config/enrichment_rules/{system_id}.yaml
    """

    def __init__(self, rules_dir: Optional[Path] = None):
        """Initialize enrichment rules engine.

        Args:
            rules_dir: Directory containing rule YAML files
                      (default: /config/enrichment_rules)
        """
        if rules_dir is None:
            # Default to config directory
            rules_dir = Path(__file__).parent.parent.parent.parent.parent / "config" / "enrichment_rules"

        self.rules_dir = rules_dir
        self._rules_cache: dict[str, dict[str, Any]] = {}

        logger.info(f"Enrichment rules engine initialized (rules_dir: {rules_dir})")

    def load_rules(self, system_id: str) -> dict[str, Any]:
        """Load enrichment rules for a system.

        Args:
            system_id: System identifier (e.g., "pathfinder", "cyberpunk")

        Returns:
            Parsed rules dictionary

        Raises:
            FileNotFoundError: If rules file doesn't exist
            yaml.YAMLError: If rules file is invalid
        """
        # Check cache first
        if system_id in self._rules_cache:
            return self._rules_cache[system_id]

        # Load from file
        rules_file = self.rules_dir / f"{system_id}.yaml"

        if not rules_file.exists():
            logger.warning(f"Rules file not found for system: {system_id}")
            # Return empty rules (no enrichment)
            return self._get_default_rules(system_id)

        logger.info(f"Loading enrichment rules: {system_id}")

        with open(rules_file, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)

        # Cache rules
        self._rules_cache[system_id] = rules

        logger.info(
            f"Loaded {len(rules.get('content_types', []))} content type rules "
            f"for {system_id}"
        )

        return rules

    def _get_default_rules(self, system_id: str) -> dict[str, Any]:
        """Get default rules when system rules file doesn't exist.

        Args:
            system_id: System identifier

        Returns:
            Default rules dictionary
        """
        return {
            "version": "1.0",
            "system_id": system_id,
            "system_name": system_id.capitalize(),
            "content_types": [
                {
                    "name": "general_text",
                    "description": "General text content",
                    "fallback": True,
                }
            ],
            "section_keywords": {},
            "system_tags": [system_id],
        }

    def classify_content_type(
        self,
        text: str,
        block_type: str,
        system_id: str,
    ) -> str:
        """Classify content type using deterministic rules.

        Args:
            text: Block text content
            block_type: Canonical block type
            system_id: System identifier

        Returns:
            Content type name (e.g., "statblock", "spell", "flavor_text")
        """
        rules = self.load_rules(system_id)
        content_types = rules.get("content_types", [])

        # Try each content type in order
        for content_type_rule in content_types:
            if content_type_rule.get("fallback", False):
                # Save fallback for last
                fallback_type = content_type_rule["name"]
                continue

            if self._matches_content_type(text, content_type_rule):
                return content_type_rule["name"]

        # Use fallback if no matches
        return fallback_type if 'fallback_type' in locals() else "general_text"

    def _matches_content_type(
        self,
        text: str,
        content_type_rule: dict[str, Any],
    ) -> bool:
        """Check if text matches a content type rule.

        Args:
            text: Block text content
            content_type_rule: Content type rule definition

        Returns:
            True if text matches rule criteria
        """
        match_count = 0
        min_matches = content_type_rule.get("min_matches", 1)

        # Check regex patterns
        patterns = content_type_rule.get("patterns", [])
        for pattern_def in patterns:
            regex = pattern_def.get("regex")
            if regex and re.search(regex, text, re.MULTILINE | re.IGNORECASE):
                match_count += 1

        # Check keywords
        keywords = content_type_rule.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in text.lower():
                match_count += 1

        return match_count >= min_matches

    def get_system_tags(self, system_id: str) -> list[str]:
        """Get system-wide tags for a system.

        Args:
            system_id: System identifier

        Returns:
            List of system tags
        """
        rules = self.load_rules(system_id)
        return rules.get("system_tags", [system_id])

    def get_rules_version(self, system_id: str) -> str:
        """Get rules version for a system.

        Args:
            system_id: System identifier

        Returns:
            Rules version string
        """
        rules = self.load_rules(system_id)
        return rules.get("version", "1.0")
