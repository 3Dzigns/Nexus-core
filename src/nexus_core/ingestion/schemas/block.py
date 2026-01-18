"""Canonical block schema for normalized content.

Per INGESTION_ARCHITECTURE_v1.0.md Section 8.2:
- Common schema for both Docling and Unstructured outputs
- Preserves tool metadata while enabling uniform processing
- Supports enrichment and chunking phases

Requirements: FR-015
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CanonicalBlock:
    """Canonical block representation for normalized content.

    This schema bridges extractor-specific outputs to a common format
    for enrichment and chunking stages.

    Per ARTIFACT_CONTRACT_v1.0.md Section 5.3:
    - block_id: Unique identifier for block
    - block_type: Semantic type (title, paragraph, table, etc.)
    - text_content: Extracted text
    - page_number: Source page (if available)
    - ocr_flag: Whether text derived from OCR
    - tool_origin: Source extractor (docling or unstructured)
    - doc_id: Parent document identifier

    Additional fields:
    - bbox: Bounding box coordinates (optional)
    - order_index: Sequential position in document
    - hierarchy_level: Nesting depth (0 = root)
    - parent_block_id: Parent block for nested content (optional)
    - metadata: Tool-specific metadata preservation
    """

    # Required fields (per ARTIFACT_CONTRACT)
    block_id: str
    block_type: str
    text_content: str
    page_number: Optional[int]
    ocr_flag: bool
    tool_origin: str  # "docling" or "unstructured"
    doc_id: str

    # Structural fields
    order_index: int = 0
    hierarchy_level: int = 0
    parent_block_id: Optional[str] = None

    # Spatial information (optional)
    bbox: Optional[dict[str, float]] = None  # {x, y, width, height}

    # Metadata preservation
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert block to dictionary for JSON serialization.

        Returns:
            Dictionary representation of block
        """
        return {
            "block_id": self.block_id,
            "block_type": self.block_type,
            "text_content": self.text_content,
            "page_number": self.page_number,
            "ocr_flag": self.ocr_flag,
            "tool_origin": self.tool_origin,
            "doc_id": self.doc_id,
            "order_index": self.order_index,
            "hierarchy_level": self.hierarchy_level,
            "parent_block_id": self.parent_block_id,
            "bbox": self.bbox,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalBlock":
        """Create block from dictionary.

        Args:
            data: Dictionary with block fields

        Returns:
            CanonicalBlock instance
        """
        return cls(
            block_id=data["block_id"],
            block_type=data["block_type"],
            text_content=data["text_content"],
            page_number=data.get("page_number"),
            ocr_flag=data["ocr_flag"],
            tool_origin=data["tool_origin"],
            doc_id=data["doc_id"],
            order_index=data.get("order_index", 0),
            hierarchy_level=data.get("hierarchy_level", 0),
            parent_block_id=data.get("parent_block_id"),
            bbox=data.get("bbox"),
            metadata=data.get("metadata", {}),
        )

    @property
    def has_spatial_info(self) -> bool:
        """Check if block has bounding box information.

        Returns:
            True if bbox is present
        """
        return self.bbox is not None

    @property
    def is_ocr_derived(self) -> bool:
        """Check if text was derived from OCR.

        Returns:
            True if OCR was used
        """
        return self.ocr_flag

    def get_text_length(self) -> int:
        """Get length of text content.

        Returns:
            Character count
        """
        return len(self.text_content)
