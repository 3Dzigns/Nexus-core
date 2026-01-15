"""Health check endpoint for Nexus Core API.

Reference:
- DEPLOYMENT_v1.0.md Section 4
- PHASE_0_INITIALIZATION_PROMPT_v1.0.md

Task ID: PHASE0-INIT-006

Health endpoint returns:
{
    "status": "healthy" | "unhealthy",
    "checks": {
        "database": "ok" | "error",
        "transfer_station": "ok" | "error",
        "environment": "ok" | "error",
        "tool_versions": "ok" | "error"
    },
    "timestamp": "ISO 8601 timestamp"
}
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings, get_settings
from nexus_core.db import get_async_session
from nexus_core.health import HealthCheckResult, run_all_checks

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResult,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def health_check(
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> HealthCheckResult:
    """Health check endpoint.

    Verifies:
    - Database connectivity
    - Transfer Station path mounted
    - Required environment variables present
    - Tool versions match minimums

    Returns:
        HealthCheckResult with status and individual check results.
    """
    result = await run_all_checks(session=session, settings=settings)

    # Set HTTP status code based on health
    if result.status != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result


@router.get("/ready", response_model=dict[str, str])
async def readiness_check(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Kubernetes-style readiness probe.

    Checks if the service is ready to accept traffic.
    Simpler than full health check - just verifies database connectivity.

    Returns:
        Simple status object.
    """
    from nexus_core.health import check_database

    result = await check_database(session)

    if result.status.value == "ok":
        return {"status": "ready"}
    return {"status": "not ready", "message": result.message or "Database check failed"}


@router.get("/live", response_model=dict[str, str])
async def liveness_check() -> dict[str, str]:
    """Kubernetes-style liveness probe.

    Simply returns OK to indicate the process is alive.

    Returns:
        Simple status object.
    """
    return {"status": "alive"}
