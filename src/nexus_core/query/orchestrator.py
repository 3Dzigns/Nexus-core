"""Query orchestrator - main entry point for query execution.

Coordinates all query subsystems:
- Authentication and role validation
- Scope resolution and enforcement
- Query classification
- Retrieval execution
- Synthesis (if needed)
- Response assembly

Reference: QUERY_IMPLEMENTATION_PROMPT_v1.0.md, FR-027 through FR-034
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import get_settings
from nexus_core.ingestion.embeddings.generator import EmbeddingGenerator
from nexus_core.query.classification.classifier import QueryClassifier
from nexus_core.query.response import ResponseBuilder
from nexus_core.query.retrieval.hybrid import HybridRetriever
from nexus_core.query.schemas import QueryClassification, QueryResponse, Role
from nexus_core.query.scope.enforcer import ScopeEnforcer
from nexus_core.query.scope.resolver import ScopeResolver
from nexus_core.query.synthesis import QuerySynthesizer

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """Orchestrates query execution through all phases.

    Execution Flow:
    1. Scope resolution (from JWT claims)
    2. Scope enforcement (validate sources exist)
    3. Query classification (DIRECT/RETRIEVAL/SYNTHESIS)
    4. Short-circuit rules (no sources, direct commands)
    5. Retrieval (keyword/vector/hybrid)
    6. Reclassification (single vs multi-chunk)
    7. Synthesis (if SYNTHESIS classification)
    8. Response assembly

    All operations are logged for audit trail.
    """

    def __init__(self, db: AsyncSession):
        """Initialize query orchestrator.

        Args:
            db: Database session
        """
        self.db = db
        self.settings = get_settings()

        # Initialize subsystems
        self.scope_resolver = ScopeResolver()
        self.scope_enforcer = ScopeEnforcer(db)
        self.classifier = QueryClassifier()

        # Initialize retrieval with shared embedding generator
        self.embedding_generator = EmbeddingGenerator()
        self.retriever = HybridRetriever(
            db,
            embedding_generator=self.embedding_generator,
            top_k=self.settings.retrieval_top_k,
            alpha=self.settings.retrieval_hybrid_alpha,
        )

        # Initialize synthesis
        self.synthesizer = QuerySynthesizer()

        # Initialize response builder
        self.response_builder = ResponseBuilder()

        logger.info("Query orchestrator initialized")

    async def execute(
        self,
        query_text: str,
        user_id: str,
        role: Role,
        game_id: Optional[str] = None,
        games_owned: Optional[list[str]] = None,
    ) -> QueryResponse:
        """Execute query through full pipeline.

        Args:
            query_text: Query text from user
            user_id: User UUID (from JWT sub)
            role: User role (from JWT role)
            game_id: Active game context (from JWT active_game_id)
            games_owned: Games owned by GM (from JWT games_owned)

        Returns:
            Query response with text and citations
        """
        logger.info(
            f"Query execution started (user: {user_id}, role: {role}, "
            f"game: {game_id}, query: {query_text[:100]})"
        )

        # Phase 1: Scope resolution
        from nexus_core.query.schemas import JWTClaims

        claims = JWTClaims(
            sub=user_id,
            role=role,
            active_game_id=game_id,
            games_owned=games_owned or [],
            tier="FREE",  # Default tier
            exp=0,  # Placeholder
            iss="",  # Placeholder
        )

        scope = self.scope_resolver.resolve(claims)

        # Phase 2: Scope enforcement
        enforcement = await self.scope_enforcer.validate_scope(scope)

        # Phase 3: Initial classification (before retrieval)
        classification = await self.classifier.classify(query_text, enforcement)

        logger.info(f"Initial classification: {classification}")

        # Phase 4: Handle short-circuit rules
        # Rule 1: No sources
        if not enforcement.has_sources:
            return self.response_builder.build_no_sources_response(classification)

        # Rule 2: Direct command
        if classification.classification == QueryClassification.DIRECT:
            doc_ids = await self.scope_enforcer.get_accessible_doc_ids(scope)
            return self.response_builder.build_direct_command_response(
                classification, doc_ids
            )

        # Phase 5: Retrieval execution
        logger.info("Executing retrieval")

        # Select retrieval strategy based on query complexity
        if classification.complexity.token_count < self.settings.retrieval_keyword_threshold:
            # Short query: keyword-only
            ranked_chunks = await self.retriever.retrieve_keyword_only(query_text, scope)
        elif classification.complexity.token_count > 50:
            # Long query: vector-only
            ranked_chunks = await self.retriever.retrieve_vector_only(query_text, scope)
        else:
            # Medium query: hybrid
            ranked_chunks = await self.retriever.retrieve(query_text, scope)

        logger.info(f"Retrieval complete: {len(ranked_chunks)} results")

        # Phase 6: Reclassification with retrieval results
        classification = await self.classifier.classify(
            query_text, enforcement, retrieval_results=ranked_chunks
        )

        logger.info(f"Final classification: {classification}")

        # Phase 7: Handle classification-based routing
        if classification.classification == QueryClassification.RETRIEVAL:
            # Single high-confidence chunk or retrieval-only response
            if len(ranked_chunks) == 1:
                return self.response_builder.build_single_chunk_response(
                    classification, ranked_chunks[0]
                )
            else:
                return self.response_builder.build_retrieval_response(
                    classification, ranked_chunks
                )

        elif classification.classification == QueryClassification.SYNTHESIS:
            # Phase 8: Synthesis execution
            logger.info("Executing synthesis")

            synthesis = await self.synthesizer.synthesize(query_text, ranked_chunks)

            return self.response_builder.build_synthesis_response(
                classification, synthesis
            )

        else:
            # Fallback: return retrieval results
            logger.warning(f"Unexpected classification: {classification.classification}")
            return self.response_builder.build_retrieval_response(
                classification, ranked_chunks
            )
