"""Chunking algorithm for document processing.

Per ARTIFACT_CONTRACT_v1.0.md Section 5.5:
- Generate dual chunk sets (Docling + Unstructured)
- Respect section boundaries
- Deterministic chunk IDs (NFR-010): {doc_id}::{tool_id}::{chunk_sha256[:16]}
- Output: chunks/<doc_id>/docling_chunks.jsonl and unstructured_chunks.jsonl

Requirements: FR-019, FR-020, NFR-010
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from nexus_core.ingestion.schemas.block import CanonicalBlock

logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for chunking algorithm.

    Attributes:
        max_chunk_size: Maximum characters per chunk
        overlap_size: Character overlap between chunks
        respect_sections: Whether to avoid splitting across sections
        min_chunk_size: Minimum characters per chunk
    """

    max_chunk_size: int = 1000
    overlap_size: int = 100
    respect_sections: bool = True
    min_chunk_size: int = 100


class Chunker:
    """Chunks enriched manifests into retrievable units."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize chunker.

        Args:
            config: Chunking configuration (uses defaults if not provided)
        """
        self.config = config or ChunkingConfig()
        logger.info(
            f"Chunker initialized (max_size={self.config.max_chunk_size}, "
            f"overlap={self.config.overlap_size})"
        )

    async def chunk(
        self,
        enriched_manifest_path: str,
        doc_id: str,
        artifacts_root: Path,
        tool_origin: str,
    ) -> str:
        """Chunk an enriched manifest.

        Args:
            enriched_manifest_path: Path to enriched manifest
            doc_id: Document identifier
            artifacts_root: Artifacts root directory
            tool_origin: Tool that produced manifest (docling or unstructured)

        Returns:
            Path to chunks file (relative to artifacts root)
        """
        logger.info(f"Chunking {tool_origin} manifest: {doc_id}")

        # Load enriched manifest
        with open(enriched_manifest_path, "r", encoding="utf-8") as f:
            enriched_data = json.load(f)

        # Convert blocks from dict to CanonicalBlock
        blocks = [
            CanonicalBlock.from_dict(block_dict)
            for block_dict in enriched_data.get("blocks", [])
        ]

        # Generate chunks
        chunks = self._create_chunks(blocks, doc_id, tool_origin, enriched_data)

        # Write chunks to JSONL
        chunks_dir = artifacts_root / "chunks" / doc_id
        chunks_dir.mkdir(parents=True, exist_ok=True)

        chunks_path = chunks_dir / f"{tool_origin}_chunks.jsonl"
        with open(chunks_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        logger.info(
            f"Chunking complete: {doc_id} ({tool_origin}, {len(chunks)} chunks)"
        )

        return str(chunks_path.relative_to(artifacts_root))

    def _create_chunks(
        self,
        blocks: list[CanonicalBlock],
        doc_id: str,
        tool_origin: str,
        enriched_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Create chunks from blocks.

        Args:
            blocks: List of canonical blocks
            doc_id: Document identifier
            tool_origin: Tool identifier
            enriched_data: Enriched manifest data (for metadata)

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        chunk_index = 0

        if self.config.respect_sections:
            # Group by section, then chunk within sections
            sections = self._group_by_section(blocks)

            for section_path, section_blocks in sections.items():
                section_chunks = self._chunk_section(
                    section_blocks, doc_id, tool_origin, chunk_index, enriched_data
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
        else:
            # Simple chunking without section boundaries
            chunks = self._chunk_blocks(
                blocks, doc_id, tool_origin, chunk_index, enriched_data
            )

        return chunks

    def _group_by_section(
        self,
        blocks: list[CanonicalBlock],
    ) -> dict[str, list[CanonicalBlock]]:
        """Group blocks by section path.

        Args:
            blocks: List of canonical blocks

        Returns:
            Dictionary mapping section_path to blocks
        """
        sections: dict[str, list[CanonicalBlock]] = {}

        for block in blocks:
            section_path = block.metadata.get("section_path", "Unknown")
            if section_path not in sections:
                sections[section_path] = []
            sections[section_path].append(block)

        return sections

    def _chunk_section(
        self,
        blocks: list[CanonicalBlock],
        doc_id: str,
        tool_origin: str,
        start_index: int,
        enriched_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Chunk blocks within a section.

        Args:
            blocks: Blocks in section
            doc_id: Document identifier
            tool_origin: Tool identifier
            start_index: Starting chunk index
            enriched_data: Enriched manifest data

        Returns:
            List of chunks for section
        """
        return self._chunk_blocks(blocks, doc_id, tool_origin, start_index, enriched_data)

    def _chunk_blocks(
        self,
        blocks: list[CanonicalBlock],
        doc_id: str,
        tool_origin: str,
        start_index: int,
        enriched_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Chunk a sequence of blocks.

        Args:
            blocks: List of blocks to chunk
            doc_id: Document identifier
            tool_origin: Tool identifier
            start_index: Starting chunk index
            enriched_data: Enriched manifest data

        Returns:
            List of chunks
        """
        chunks = []
        current_text = ""
        current_blocks = []
        chunk_index = start_index

        for block in blocks:
            block_text = block.text_content

            # Check if adding this block exceeds max size
            if len(current_text) + len(block_text) > self.config.max_chunk_size:
                # Create chunk from current blocks
                if current_blocks:
                    chunk = self._create_chunk(
                        current_blocks,
                        doc_id,
                        tool_origin,
                        chunk_index,
                        enriched_data,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                    # Reset with overlap (keep last block for continuity)
                    if self.config.overlap_size > 0 and len(current_blocks) > 1:
                        current_blocks = [current_blocks[-1]]
                        current_text = current_blocks[0].text_content
                    else:
                        current_blocks = []
                        current_text = ""

            # Add block to current chunk
            current_blocks.append(block)
            current_text += " " + block_text

        # Create final chunk
        if current_blocks:
            chunk = self._create_chunk(
                current_blocks, doc_id, tool_origin, chunk_index, enriched_data
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        blocks: list[CanonicalBlock],
        doc_id: str,
        tool_origin: str,
        chunk_index: int,
        enriched_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a single chunk from blocks.

        Args:
            blocks: Blocks to include in chunk
            doc_id: Document identifier
            tool_origin: Tool identifier
            chunk_index: Sequential chunk number
            enriched_data: Enriched manifest data

        Returns:
            Chunk dictionary
        """
        # Combine block text
        chunk_text = "\n\n".join(block.text_content for block in blocks)

        # Compute deterministic chunk SHA-256 (per NFR-010)
        chunk_sha256 = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()

        # Generate chunk_id: {doc_id}::{tool_id}::{chunk_sha256[:16]}
        chunk_id = f"{doc_id}::{tool_origin}::{chunk_sha256[:16]}"

        # Extract metadata from first block (representative)
        first_block = blocks[0]
        section_path = first_block.metadata.get("section_path", "Unknown")
        section_title = first_block.metadata.get("section_title", "Unknown")
        content_type = first_block.metadata.get("content_type", "general_text")
        system_tags = first_block.metadata.get("system_tags", [])

        # Create chunk
        chunk = {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "tool_origin": tool_origin,
            "chunk_text": chunk_text,
            "chunk_sha256": chunk_sha256,
            "section_path": section_path,
            "section_title": section_title,
            "content_type": content_type,
            "system_id": enriched_data.get("system_id"),
            "system_tags": system_tags,
            "chunk_index": chunk_index,
            "block_count": len(blocks),
            "metadata": {
                "enrichment_rules_version": enriched_data.get("enrichment_rules_version"),
                "block_ids": [block.block_id for block in blocks],
            },
        }

        return chunk
