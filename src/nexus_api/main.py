"""Nexus Core API - FastAPI application entry point.

Reference:
- ARCHITECTURE_v1.0.md
- DEPLOYMENT_v1.0.md
- OPENAPI_v1.0.md

Task ID: PHASE0-INIT-006
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nexus_api.routes import governance, health, validation
from nexus_core.config import get_settings
from nexus_core.db import async_engine

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Nexus Core API starting up...")
    logger.info(f"Transfer Station path: {settings.transfer_station_path}")
    logger.info(f"Database URL: {settings.database_url.split('@')[-1]}")  # Hide credentials

    yield

    # Shutdown
    logger.info("Nexus Core API shutting down...")
    await async_engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="Nexus Core API",
    description="TTRPG knowledge ingestion and AI query system",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(governance.router, tags=["Governance"])
app.include_router(validation.router, tags=["Validation"])


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint - API information."""
    return {
        "name": "Nexus Core API",
        "version": "0.1.0",
        "status": "running",
    }
