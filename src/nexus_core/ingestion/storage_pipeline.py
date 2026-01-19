"""Storage and indexing pipeline orchestrator.

Per INGESTION_ARCHITECTURE_v1.0.md Section 11:
- Coordinate: chunk storage → embeddings → FTS → vector index
- Atomic transaction per doc_id
- Rollback on failure → delete all rows for doc_id

Requirements: FR-021, FR-022
"""

import logging
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_core.config import Settings
from nexus_core.ingestion.embeddings.generator import EmbeddingGenerator
from nexus_core.ingestion.indexing.fts_indexer import FTSIndexer
from nexus_core.ingestion.indexing.vector_indexer import VectorIndexer
from nexus_core.ingestion.storage.chunk_storage import ChunkStorage
from nexus_core.ingestion.storage.embedding_storage import EmbeddingStorage
from nexus_core.models.source import Chunk, Embedding, FTSIndex, Source, ToolId

logger = logging.getLogger(__name__)


class StoragePipeline:
    """Orchestrates chunk storage, embedding generation, and indexing."""

    def __init__(self, session: AsyncSession, settings: Settings):
        """Initialize storage pipeline.

        Args:
            session: Database session
            settings: Application settings
        """
        self.session = session
        self.settings = settings
        self.artifacts_root = Path(settings.transfer_station_path) / "artifacts"

        # Initialize components
        self.chunk_storage = ChunkStorage(session)
        self.embedding_generator = EmbeddingGenerator(
            model_name=settings.embedding_model
        )
        self.embedding_storage = EmbeddingStorage(session)
        self.fts_indexer = FTSIndexer(session)
        self.vector_indexer = VectorIndexer(session)

    async def execute(self, source: Source) -> bool:
        """Execute storage and indexing pipeline for a source.

        Args:
            source: Source record from database

        Returns:
            True if pipeline succeeded, False otherwise

        Workflow:
        1. Load chunks from JSONL files (both tools)
        2. Store chunks in database
        3. Generate embeddings for all chunks
        4. Store embeddings in database
        5. Create FTS index entries
        6. Ensure vector indexes exist
        7. Commit transaction (or rollback on failure)
        """
        doc_id = source.doc_id
        logger.info(f"Starting storage pipeline: {doc_id}")

        try:
            # Step 1: Get chunk file paths
            docling_chunks_path = self.artifacts_root / "chunks" / doc_id / "docling_chunks.jsonl"
            unstructured_chunks_path = (
                self.artifacts_root / "chunks" / doc_id / "unstructured_chunks.jsonl"
            )

            if not docling_chunks_path.exists() or not unstructured_chunks_path.exists():
                logger.error(f"Missing chunk files for {doc_id}")
                return False

            # Step 2: Store Docling chunks
            docling_count = await self.chunk_storage.store_chunks(
                docling_chunks_path, doc_id, ToolId.DOCLING
            )

            # Step 3: Store Unstructured chunks
            unstructured_count = await self.chunk_storage.store_chunks(
                unstructured_chunks_path, doc_id, ToolId.UNSTRUCTURED
            )

            total_chunks = docling_count + unstructured_count
            logger.info(
                f"Stored {total_chunks} chunks for {doc_id} "
                f"(Docling: {docling_count}, Unstructured: {unstructured_count})"
            )

            # Step 4: Get stored chunks from database
            from sqlalchemy import select

            result = await self.session.execute(
                select(Chunk).where(Chunk.doc_id == doc_id)
            )
            chunks = result.scalars().all()

            if not chunks:
                logger.error(f"No chunks found in database for {doc_id}")
                return False

            # Step 5: Generate embeddings for all chunks
            logger.info(f"Generating embeddings for {len(chunks)} chunks")

            chunk_texts = [chunk.chunk_text for chunk in chunks]
            embeddings = await self.embedding_generator.generate_embeddings_batch(
                chunk_texts
            )

            # Step 6: Store embeddings
            embeddings_data = [
                (chunk.chunk_id, embedding)
                for chunk, embedding in zip(chunks, embeddings)
                if embedding is not None
            ]

            embeddings_count = await self.embedding_storage.store_embeddings_batch(
                embeddings_data
            )

            logger.info(f"Stored {embeddings_count} embeddings for {doc_id}")

            # Step 7: Create FTS index entries
            fts_data = [(chunk.chunk_id, chunk.chunk_text) for chunk in chunks]
            fts_count = await self.fts_indexer.index_chunks_batch(fts_data)

            logger.info(f"Indexed {fts_count} chunks for FTS")

            # Step 8: Ensure FTS GIN index exists
            await self.fts_indexer.ensure_gin_index()

            # Step 9: Ensure vector index exists (HNSW or IVFFLAT)
            vector_index_created = await self.vector_indexer.create_vector_index()

            if not vector_index_created:
                logger.warning(f"Vector index creation failed for {doc_id}")
                # Continue anyway - index can be created later

            # Commit transaction
            await self.session.commit()

            logger.info(
                f"Storage pipeline complete: {doc_id} "
                f"({total_chunks} chunks, {embeddings_count} embeddings, "
                f"{fts_count} FTS entries)"
            )

            return True

        except Exception as e:
            logger.error(f"Storage pipeline failed for {doc_id}: {e}", exc_info=True)

            # Rollback transaction
            await self.session.rollback()

            # Delete all rows for this doc_id
            await self._rollback_storage(doc_id)

            return False

    async def _rollback_storage(self, doc_id: str) -> None:
        """Delete all storage rows for a document (rollback on failure).

        Args:
            doc_id: Document identifier
        """
        logger.warning(f"Rolling back storage for {doc_id}")

        try:
            # Delete FTS entries
            await self.session.execute(
                delete(FTSIndex).where(
                    FTSIndex.chunk_id.in_(
                        select(Chunk.chunk_id).where(Chunk.doc_id == doc_id)
                    )
                )
            )

            # Delete embeddings
            await self.session.execute(
                delete(Embedding).where(
                    Embedding.chunk_id.in_(
                        select(Chunk.chunk_id).where(Chunk.doc_id == doc_id)
                    )
                )
            )

            # Delete chunks
            await self.session.execute(delete(Chunk).where(Chunk.doc_id == doc_id))

            await self.session.commit()

            logger.info(f"Storage rollback complete for {doc_id}")

        except Exception as e:
            logger.error(f"Storage rollback failed for {doc_id}: {e}")
