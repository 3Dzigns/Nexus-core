"""Section path assignment for enrichment.

Per INGESTION_ARCHITECTURE_v1.0.md Section 9.3:
- Extract section hierarchy from extractor metadata
- Fallback to page-based grouping if hierarchy missing
- Assign section_title and section_path to each block

Requirements: FR-016
"""

import logging
from typing import Optional

from nexus_core.ingestion.schemas.block import CanonicalBlock

logger = logging.getLogger(__name__)


class SectionPathAssigner:
    """Assigns section paths to canonical blocks."""

    def __init__(self):
        """Initialize section path assigner."""
        pass

    def assign_section_path(
        self,
        blocks: list[CanonicalBlock],
    ) -> list[CanonicalBlock]:
        """Assign section paths to blocks.

        Args:
            blocks: List of canonical blocks

        Returns:
            Blocks with section_path metadata added
        """
        if not blocks:
            return blocks

        # Try hierarchy-based assignment first
        if self._has_hierarchy(blocks):
            return self._assign_from_hierarchy(blocks)

        # Fallback to page-based grouping
        return self._assign_from_pages(blocks)

    def _has_hierarchy(self, blocks: list[CanonicalBlock]) -> bool:
        """Check if blocks have hierarchy information.

        Args:
            blocks: List of canonical blocks

        Returns:
            True if any block has hierarchy_level != 0
        """
        return any(
            block.hierarchy_level > 0 or block.parent_block_id is not None
            for block in blocks
        )

    def _assign_from_hierarchy(
        self,
        blocks: list[CanonicalBlock],
    ) -> list[CanonicalBlock]:
        """Assign section paths based on block hierarchy.

        Args:
            blocks: List of canonical blocks

        Returns:
            Blocks with section paths assigned
        """
        logger.debug("Assigning section paths from hierarchy")

        current_section_stack: list[str] = []

        for block in blocks:
            # Update section stack based on hierarchy
            if block.block_type in ("title", "heading", "header"):
                # This is a section heading
                level = block.hierarchy_level

                # Adjust stack to current level
                while len(current_section_stack) > level:
                    current_section_stack.pop()

                # Add this section
                section_title = block.text_content[:50]  # Truncate for readability
                if len(current_section_stack) == level:
                    current_section_stack.append(section_title)
                else:
                    current_section_stack.append(section_title)

            # Assign section path
            if current_section_stack:
                block.metadata["section_title"] = current_section_stack[-1]
                block.metadata["section_path"] = " > ".join(current_section_stack)
            else:
                block.metadata["section_title"] = "Document Root"
                block.metadata["section_path"] = "Document Root"

        return blocks

    def _assign_from_pages(
        self,
        blocks: list[CanonicalBlock],
    ) -> list[CanonicalBlock]:
        """Assign section paths based on page numbers (fallback).

        Args:
            blocks: List of canonical blocks

        Returns:
            Blocks with section paths assigned
        """
        logger.debug("Assigning section paths from pages (fallback)")

        for block in blocks:
            page_num = block.page_number if block.page_number is not None else 1
            section_title = f"Page {page_num}"
            block.metadata["section_title"] = section_title
            block.metadata["section_path"] = section_title

        return blocks
