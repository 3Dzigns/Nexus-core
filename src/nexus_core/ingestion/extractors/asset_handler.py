"""Asset extraction and storage handler.

Per ARTIFACT_CONTRACT_v1.0.md Section 3:
- Extract images from both Docling and Unstructured outputs
- Store in: artifacts/assets/<doc_id>/images/
- Generate asset references for manifest linkage
- Ensure unique filenames across both extractors

Requirements: FR-011
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AssetHandler:
    """Handler for extracting and storing document assets (images, etc.)."""

    def __init__(self, assets_root: Path):
        """Initialize asset handler.

        Args:
            assets_root: Root directory for assets (artifacts/assets)
        """
        self.assets_root = assets_root

    def get_asset_dir(self, doc_id: str) -> Path:
        """Get asset directory for a document.

        Args:
            doc_id: Document identifier

        Returns:
            Path to asset directory (creates if not exists)
        """
        asset_dir = self.assets_root / doc_id / "images"
        asset_dir.mkdir(parents=True, exist_ok=True)
        return asset_dir

    def save_image(
        self,
        doc_id: str,
        image_data: bytes,
        image_name: str,
        tool_prefix: str = "",
    ) -> str:
        """Save an image asset to disk.

        Args:
            doc_id: Document identifier
            image_data: Raw image bytes
            image_name: Original image filename
            tool_prefix: Optional prefix (docling_ or unstructured_)

        Returns:
            Path to saved image (relative to artifacts root)

        Example:
            save_image("doc_123", b"...", "page1.png", "docling_")
            -> "artifacts/assets/doc_123/images/docling_page1.png"
        """
        asset_dir = self.get_asset_dir(doc_id)

        # Add tool prefix to avoid filename collisions
        filename = f"{tool_prefix}{image_name}" if tool_prefix else image_name
        image_path = asset_dir / filename

        # Write image data
        with open(image_path, "wb") as f:
            f.write(image_data)

        logger.debug(f"Saved image: {image_path}")

        # Return relative path from artifacts root
        return str(image_path.relative_to(self.assets_root.parent))

    def copy_image(
        self,
        doc_id: str,
        source_path: str,
        image_name: Optional[str] = None,
        tool_prefix: str = "",
    ) -> str:
        """Copy an image from source path to asset directory.

        Args:
            doc_id: Document identifier
            source_path: Path to source image file
            image_name: Optional custom filename (uses source name if not provided)
            tool_prefix: Optional prefix (docling_ or unstructured_)

        Returns:
            Path to saved image (relative to artifacts root)
        """
        asset_dir = self.get_asset_dir(doc_id)
        source = Path(source_path)

        # Determine filename
        if image_name is None:
            image_name = source.name

        # Add tool prefix to avoid filename collisions
        filename = f"{tool_prefix}{image_name}" if tool_prefix else image_name
        dest_path = asset_dir / filename

        # Copy image file
        shutil.copy2(source, dest_path)

        logger.debug(f"Copied image: {source} -> {dest_path}")

        # Return relative path from artifacts root
        return str(dest_path.relative_to(self.assets_root.parent))

    def list_assets(self, doc_id: str) -> list[str]:
        """List all assets for a document.

        Args:
            doc_id: Document identifier

        Returns:
            List of asset paths (relative to artifacts root)
        """
        asset_dir = self.get_asset_dir(doc_id)

        if not asset_dir.exists():
            return []

        assets = []
        for asset_file in asset_dir.iterdir():
            if asset_file.is_file():
                rel_path = str(asset_file.relative_to(self.assets_root.parent))
                assets.append(rel_path)

        return assets

    def delete_assets(self, doc_id: str) -> None:
        """Delete all assets for a document (rollback on failure).

        Args:
            doc_id: Document identifier
        """
        asset_dir = self.assets_root / doc_id

        if asset_dir.exists():
            shutil.rmtree(asset_dir)
            logger.info(f"Deleted assets for {doc_id}")
