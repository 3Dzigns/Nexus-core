"""Pydantic schemas for query subsystem.

Reference: QUERY_IMPLEMENTATION_PROMPT_v1.0.md, OPENAPI_v1.0.md
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """User role enumeration."""

    PLAYER = "PLAYER"
    GM = "GM"
    ADMIN = "ADMIN"


class QueryClassification(str, Enum):
    """Query classification levels."""

    DIRECT = "DIRECT"
    RETRIEVAL = "RETRIEVAL"
    SYNTHESIS = "SYNTHESIS"


class JWTClaims(BaseModel):
    """JWT token claims per JWT_SPEC_v1.0.md.

    All fields are validated and extracted from JWT token.
    Never accept these values from client input.
    """

    sub: str = Field(..., description="User UUID")
    role: Role = Field(..., description="User role (PLAYER|GM|ADMIN)")
    active_game_id: Optional[str] = Field(
        None, description="Active game context (game UUID or null)"
    )
    games_owned: list[str] = Field(
        default_factory=list, description="Games owned by user (GM role only)"
    )
    tier: str = Field(default="FREE", description="User tier (FREE|BASIC|PRO)")
    exp: int = Field(..., description="Token expiration timestamp")
    iss: str = Field(..., description="Token issuer")


class QueryRequest(BaseModel):
    """Query request from client.

    Reference: OPENAPI_v1.0.md POST /query
    """

    query_text: str = Field(..., min_length=1, max_length=2000)


class SourceCitation(BaseModel):
    """Source citation in query response."""

    doc_id: str
    chunk_id: str
    tool_id: str


class QueryResponse(BaseModel):
    """Query response to client.

    Reference: OPENAPI_v1.0.md POST /query
    """

    response_text: str
    sources: list[SourceCitation]
    classification: Optional[QueryClassification] = None  # For debugging
    rule_path: Optional[str] = None  # For logging/debugging
