"""Health check implementations for Nexus Core services.

Reference:
- DEPLOYMENT_v1.0.md Section 4
- PHASE_0_INITIALIZATION_PROMPT_v1.0.md

Task ID: PHASE0-INIT-006

Health checks verify:
- Database connectivity
- Transfer Station path mounted and accessible
- Required environment variables present
- Tool versions match minimums
"""

import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings, get_settings


class HealthStatus(str, Enum):
    """Health check status values."""

    OK = "ok"
    ERROR = "error"


class CheckResult(BaseModel):
    """Result of a single health check."""

    status: HealthStatus
    message: Optional[str] = None


class HealthCheckResult(BaseModel):
    """Complete health check response.

    Reference: PHASE_0_INITIALIZATION_PROMPT_v1.0.md Section 4
    """

    status: str  # "healthy" or "unhealthy"
    checks: dict[str, str]  # Each check: "ok" or "error"
    timestamp: str  # ISO 8601 format

    @classmethod
    def from_checks(cls, checks: dict[str, CheckResult]) -> "HealthCheckResult":
        """Create HealthCheckResult from individual check results."""
        check_statuses = {name: result.status.value for name, result in checks.items()}
        overall_healthy = all(r.status == HealthStatus.OK for r in checks.values())

        return cls(
            status="healthy" if overall_healthy else "unhealthy",
            checks=check_statuses,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def check_database(session: Optional[AsyncSession] = None) -> CheckResult:
    """Check database connectivity.

    Args:
        session: Optional database session. If not provided, creates a new one.

    Returns:
        CheckResult indicating database status.
    """
    try:
        if session is None:
            # Import here to avoid circular imports
            from nexus_core.db import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
        else:
            result = await session.execute(text("SELECT 1"))
            result.scalar()

        return CheckResult(status=HealthStatus.OK)

    except Exception as e:
        return CheckResult(status=HealthStatus.ERROR, message=str(e))


def check_transfer_station(settings: Optional[Settings] = None) -> CheckResult:
    """Check Transfer Station path is mounted and accessible.

    Args:
        settings: Optional settings. If not provided, uses get_settings().

    Returns:
        CheckResult indicating Transfer Station status.
    """
    if settings is None:
        settings = get_settings()

    path = Path(settings.transfer_station_path)

    # Check path exists
    if not path.exists():
        return CheckResult(
            status=HealthStatus.ERROR,
            message=f"Transfer Station path does not exist: {path}",
        )

    # Check path is a directory
    if not path.is_dir():
        return CheckResult(
            status=HealthStatus.ERROR,
            message=f"Transfer Station path is not a directory: {path}",
        )

    # Check path is writable
    if not os.access(path, os.W_OK):
        return CheckResult(
            status=HealthStatus.ERROR,
            message=f"Transfer Station path is not writable: {path}",
        )

    # Check required subdirectories exist
    required_dirs = ["sources", "quarantine", "artifacts", "logs"]
    missing_dirs = [d for d in required_dirs if not (path / d).exists()]

    if missing_dirs:
        return CheckResult(
            status=HealthStatus.ERROR,
            message=f"Missing required directories: {missing_dirs}",
        )

    return CheckResult(status=HealthStatus.OK)


def check_environment(settings: Optional[Settings] = None) -> CheckResult:
    """Check required environment variables are present.

    Args:
        settings: Optional settings. If not provided, uses get_settings().

    Returns:
        CheckResult indicating environment status.
    """
    if settings is None:
        settings = get_settings()

    # Required environment variables for basic operation
    required_vars = [
        ("DATABASE_URL", settings.database_url),
        ("TRANSFER_STATION_PATH", settings.transfer_station_path),
    ]

    missing = [name for name, value in required_vars if not value]

    if missing:
        return CheckResult(
            status=HealthStatus.ERROR,
            message=f"Missing required environment variables: {missing}",
        )

    return CheckResult(status=HealthStatus.OK)


def check_tool_versions(settings: Optional[Settings] = None) -> CheckResult:
    """Check tool versions meet minimum requirements.

    Reference: TOOL_VERSIONS_v1.0.md

    Args:
        settings: Optional settings. If not provided, uses get_settings().

    Returns:
        CheckResult indicating tool version status.
    """
    if settings is None:
        settings = get_settings()

    # Minimum versions from TOOL_VERSIONS_v1.0.md
    min_versions = {
        "docling": (1, 0, 0),
        "unstructured": (0, 10, 0),
    }

    def parse_version(version_string: str) -> tuple[int, ...]:
        """Parse version string like 'toolname/1.2.3' to tuple (1, 2, 3)."""
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_string)
        if match:
            return tuple(int(x) for x in match.groups())
        return (0, 0, 0)

    # Check Docling version
    docling_version = parse_version(settings.docling_version)
    if docling_version < min_versions["docling"]:
        return CheckResult(
            status=HealthStatus.ERROR,
            message=f"Docling version {settings.docling_version} below minimum {min_versions['docling']}",
        )

    # Check Unstructured version
    unstructured_version = parse_version(settings.unstructured_version)
    if unstructured_version < min_versions["unstructured"]:
        return CheckResult(
            status=HealthStatus.ERROR,
            message=f"Unstructured version {settings.unstructured_version} below minimum {min_versions['unstructured']}",
        )

    return CheckResult(status=HealthStatus.OK)


async def run_all_checks(
    session: Optional[AsyncSession] = None,
    settings: Optional[Settings] = None,
) -> HealthCheckResult:
    """Run all health checks and return combined result.

    Args:
        session: Optional database session.
        settings: Optional settings.

    Returns:
        HealthCheckResult with all check statuses.
    """
    if settings is None:
        settings = get_settings()

    checks = {
        "database": await check_database(session),
        "transfer_station": check_transfer_station(settings),
        "environment": check_environment(settings),
        "tool_versions": check_tool_versions(settings),
    }

    return HealthCheckResult.from_checks(checks)
