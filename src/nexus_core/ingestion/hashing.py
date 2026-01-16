"""File hashing and document identity creation.

Per CLAUDE.md and ARTIFACT_CONTRACT_v1.0.md Section 4.1:
- doc_id format: <sanitized_filename>__<sha256>
- Allowed characters: A-Z a-z 0-9 . _ -
- Max length: 120 chars
"""

import hashlib
import re
from pathlib import Path


def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Absolute path to the file

    Returns:
        SHA-256 hash as hexadecimal string

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def sanitize_filename(filename: str, max_length: int = 120) -> str:
    """Sanitize filename to allowed character set.

    Per CLAUDE.md:
    - Allowed characters: A-Z a-z 0-9 . _ -
    - Replace all other characters with underscore
    - Truncate to max_length if necessary
    - Remove file extension for doc_id construction

    Args:
        filename: Original filename
        max_length: Maximum length (default 120)

    Returns:
        Sanitized filename without extension
    """
    # Remove file extension
    name_without_ext = Path(filename).stem

    # Replace disallowed characters with underscore
    # Allowed: A-Z a-z 0-9 . _ -
    sanitized = re.sub(r'[^A-Za-z0-9._-]', '_', name_without_ext)

    # Truncate if necessary
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def create_doc_id(filename: str, sha256: str) -> str:
    """Create doc_id from filename and SHA-256 hash.

    Format: <sanitized_filename>__<sha256>

    Per ARTIFACT_CONTRACT_v1.0.md Section 4.1:
    - doc_id is the primary identifier for all artifacts
    - Format ensures uniqueness via SHA-256
    - Sanitized filename provides human readability

    Args:
        filename: Original filename
        sha256: SHA-256 hash (hex string)

    Returns:
        doc_id string

    Note:
        Total length is constrained by database schema (max 255 chars).
        Filename is truncated to ensure doc_id fits within limits.
        SHA-256 hex is 64 chars + separator __ (2 chars) = 66 chars reserved.
        Therefore, sanitized filename max = 255 - 66 = 189 chars.
        Using 120 as practical limit per CLAUDE.md.
    """
    sanitized = sanitize_filename(filename, max_length=120)

    # Format: <filename>__<sha256>
    doc_id = f"{sanitized}__{sha256}"

    return doc_id
