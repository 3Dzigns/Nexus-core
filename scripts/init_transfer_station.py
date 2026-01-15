#!/usr/bin/env python3
"""Initialize Transfer Station directory structure.

Reference:
- PHASE_0_INITIALIZATION_PROMPT_v1.0.md
- INGESTION_ARCHITECTURE_v1.0.md

Task ID: PHASE0-INIT-004

This script creates the required directory structure for the Transfer Station.
It is idempotent - running it multiple times is safe and will not overwrite existing data.

Directory Structure:
    Transfer_Station/
    ├── sources/                    # User dropzone for source files
    ├── quarantine/                 # Denied or suspicious sources
    ├── artifacts/
    │   ├── manifests/<doc_id>/
    │   │   ├── raw/
    │   │   ├── normalized/
    │   │   └── enriched/
    │   ├── chunks/<doc_id>/
    │   ├── assets/<doc_id>/images/
    │   └── reports/<doc_id>/
    └── logs/
        └── ingestion/

Usage:
    python scripts/init_transfer_station.py [--path /custom/path]

Environment:
    TRANSFER_STATION_PATH: Override default path (default: /transfer_station in container)
"""

import argparse
import os
import sys
from pathlib import Path


# Default paths
DEFAULT_CONTAINER_PATH = "/transfer_station"
DEFAULT_WINDOWS_PATH = r"E:\Transfer_Station"


def get_transfer_station_path() -> Path:
    """Get Transfer Station path from environment or default.

    Returns:
        Path to Transfer Station root directory.
    """
    env_path = os.getenv("TRANSFER_STATION_PATH")
    if env_path:
        return Path(env_path)

    # Use container path if running in Docker, otherwise Windows default
    if os.path.exists("/transfer_station"):
        return Path(DEFAULT_CONTAINER_PATH)
    return Path(DEFAULT_WINDOWS_PATH)


def create_directory_structure(root: Path, verbose: bool = True) -> bool:
    """Create the Transfer Station directory structure.

    Args:
        root: Root path for Transfer Station.
        verbose: Print progress messages.

    Returns:
        True if successful, False otherwise.
    """
    # Define directory structure
    directories = [
        # Top-level directories
        root / "sources",
        root / "quarantine",
        # Artifacts structure
        root / "artifacts" / "manifests",
        root / "artifacts" / "chunks",
        root / "artifacts" / "assets",
        root / "artifacts" / "reports",
        # Logs
        root / "logs" / "ingestion",
    ]

    try:
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            if verbose:
                print(f"  Created: {directory}")

        return True

    except PermissionError as e:
        print(f"ERROR: Permission denied creating directory: {e}", file=sys.stderr)
        return False
    except OSError as e:
        print(f"ERROR: Failed to create directory structure: {e}", file=sys.stderr)
        return False


def verify_structure(root: Path) -> bool:
    """Verify that the directory structure exists and is accessible.

    Args:
        root: Root path for Transfer Station.

    Returns:
        True if all directories exist and are writable.
    """
    required_dirs = [
        root / "sources",
        root / "quarantine",
        root / "artifacts" / "manifests",
        root / "artifacts" / "chunks",
        root / "artifacts" / "assets",
        root / "artifacts" / "reports",
        root / "logs" / "ingestion",
    ]

    all_ok = True
    for directory in required_dirs:
        if not directory.exists():
            print(f"  MISSING: {directory}", file=sys.stderr)
            all_ok = False
        elif not os.access(directory, os.W_OK):
            print(f"  NOT WRITABLE: {directory}", file=sys.stderr)
            all_ok = False
        else:
            print(f"  OK: {directory}")

    return all_ok


def create_doc_artifact_dirs(root: Path, doc_id: str) -> dict[str, Path]:
    """Create artifact directories for a specific document.

    Args:
        root: Root path for Transfer Station.
        doc_id: Document identifier.

    Returns:
        Dictionary mapping artifact type to path.
    """
    paths = {
        "manifests_raw": root / "artifacts" / "manifests" / doc_id / "raw",
        "manifests_normalized": root / "artifacts" / "manifests" / doc_id / "normalized",
        "manifests_enriched": root / "artifacts" / "manifests" / doc_id / "enriched",
        "chunks": root / "artifacts" / "chunks" / doc_id,
        "assets_images": root / "artifacts" / "assets" / doc_id / "images",
        "reports": root / "artifacts" / "reports" / doc_id,
    }

    for name, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)

    return paths


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    parser = argparse.ArgumentParser(
        description="Initialize Transfer Station directory structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--path",
        type=Path,
        help="Override Transfer Station path",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify existing structure, don't create",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )

    args = parser.parse_args()

    # Determine path
    root = args.path if args.path else get_transfer_station_path()
    verbose = not args.quiet

    print(f"Transfer Station path: {root}")
    print()

    if args.verify:
        print("Verifying directory structure...")
        if verify_structure(root):
            print("\nAll directories OK.")
            return 0
        else:
            print("\nVerification FAILED.", file=sys.stderr)
            return 1

    print("Creating directory structure...")
    if create_directory_structure(root, verbose=verbose):
        print("\nDirectory structure created successfully.")
        print("\nVerifying...")
        if verify_structure(root):
            print("\nTransfer Station initialized successfully.")
            return 0

    print("\nInitialization FAILED.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
