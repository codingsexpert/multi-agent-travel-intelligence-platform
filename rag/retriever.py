"""Production-grade RAG retrieval service with hybrid vector similarity and metadata filtering."""

from datetime import datetime, timezone
from pathlib import Path
import time
from typing import List, Dict, Any, Optional
from config.settings import Settings, get_settings
from models.rag import (
    DocumentChunk,
    DocumentMetadata,
    RAGRetrievalQuery,
    RetrievedChunk,
    RAGRetrievalResult,
    SourceTrustLevel,
)
from rag.embeddings import BaseEmbeddingService, get_embedding_service
from rag.ingestion import DocumentIngestionPipeline
from services.supabase_service import SupabaseService, supabase_service
from utils.logger import logger


SEED_DATA_DIR = Path(__file__).parent / "seed_data"


class MockKnowledgeStore:
    """In-memory vector store for DEMO_MODE, offline testing, and isolated evaluation."""

    def __init__(self):
        self.chunks: Dict[str, DocumentChunk] = {}
        self.documents: Dict[str, DocumentMetadata] = {}

    def insert_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Insert or replace document chunks by chunk_id."""
        for c in chunks:
            self.chunks[c.chunk_id] = c

    def get_all_chunks(self) -> List[DocumentChunk]:
        """Return all indexed document chunks."""
        return list(self.chunks.values())

    def clear(self) -> None:
        """Reset in-memory store."""
        self.chunks.clear()
        self.documents.clear()


# Global singleton in-memory mock store
mock_knowledge_store = MockKnowledgeStore()


class TravelKnowledgeRetriever:
    """Retrieval service managing travel knowledge queries, pgvector search, and metadata filters."""

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        supabase_svc: Optional[SupabaseService] = None,
        mock_store: Optional[MockKnowledgeStore] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.supabase_svc = supabase_svc or supabase_service
        self.embedding_service = embedding_service or get_embedding_service(self.settings)
        self.mock_store = mock_store or mock_knowledge_store
        self.pipeline = DocumentIngestionPipeline(
            embedding_service=self.embedding_service,
            settings=self.settings,
        )
        # Ensure seed documents are ingested into mock store on first access
        self._ensure_seed_data_loaded()

    def _ensure_seed_data_loaded(self) -> None:
        """Auto-seed default curated travel guides into mock store if empty."""
        if not self.mock_store.chunks and SEED_DATA_DIR.exists():
            for f in sorted(SEED_DATA_DIR.glob("*.md")):
                try:
                    content, meta = self.pipeline.extract_document_content(f)
                    doc_meta = DocumentMetadata(
                        document_id=meta.get("document_id") or f.stem,
                        title=meta.get("title") or f.stem.replace("_", " ").title(),
                        source=meta.get("source") or "Curated Travel Knowledge Base",
                        source_url=meta.get("source_url"),
                        source_trust=SourceTrustLevel(meta.get("source_trust", "CURATED")),
                        destination=meta.get("destination"),
                        country=meta.get("country"),
                        category=meta.get("category", "general"),
                        is_public=str(meta.get("is_public", "true")).lower() == "true",
                    )
                    chunks = self.pipeline.ingest_document(content, doc_meta)
                    self.mock_store.insert_chunks(chunks)
                    self.mock_store.documents[doc_meta.document_id] = doc_meta
                except Exception as e:
                    logger.warning(f"Error seeding guide '{f.name}': {e}")

    @property
    def is_demo(self) -> bool:
        """Check whether retrieval should use DEMO mode."""
        return self.settings.demo_mode or not self.supabase_svc.is_configured

    def retrieve(self, query: RAGRetrievalQuery) -> RAGRetrievalResult:
        """Execute hybrid similarity search with metadata filtering.
        
        Args:
            query: Typed RAGRetrievalQuery containing search query and filter criteria.
            
        Returns:
            RAGRetrievalResult containing top-k chunks, citations, and execution latency.
        """
        start_time = time.perf_counter()

        if not query.query.strip():
            return RAGRetrievalResult.create_empty(
                query=query.query,
                destination=query.destination,
                mode="DEMO" if self.is_demo else "LIVE",
            )

        # 1. Attempt live Supabase pgvector retrieval if live mode is enabled
        result = None
        if not self.is_demo:
            try:
                result = self._retrieve_live_supabase(query)
            except Exception as e:
                logger.warning(f"Live pgvector retrieval failed ({e}); falling back to in-memory store.")

        # 2. In-memory / Mock retrieval (DEMO_MODE or fallback)
        if result is None:
            result = self._retrieve_in_memory(query)

        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        try:
            from services.observability_service import observability_service
            chunks_list = result.results
            top_score = max([c.similarity_score for c in chunks_list], default=0.0) if chunks_list else 0.0
            observability_service.trace_rag_retrieval(
                query=query.query,
                destination=query.destination,
                retrieved_count=len(chunks_list),
                source_ids=[c.chunk_id for c in chunks_list],
                top_score=top_score,
                duration_ms=result.latency_ms,
                similarity_threshold=query.min_similarity,
                metadata_filters={
                    "destination": query.destination,
                    "category": query.category,
                    "country": query.country,
                },
                mode=result.mode,
            )
        except Exception as e:
            logger.debug(f"[TravelKnowledgeRetriever] Non-blocking observability trace skipped: {e}")

        return result

    def _retrieve_in_memory(self, query: RAGRetrievalQuery) -> RAGRetrievalResult:
        """Perform semantic cosine similarity and metadata filtering over in-memory store."""
        query_vec = self.embedding_service.embed_query(query.query)
        all_chunks = self.mock_store.get_all_chunks()

        scored_candidates: List[RetrievedChunk] = []

        for chunk in all_chunks:
            # 1. Ownership & Public Visibility Filter (Private document isolation)
            if chunk.is_public:
                if not query.include_public:
                    continue
            else:
                # Private document: MUST match user_id
                if not query.user_id or chunk.user_id != query.user_id:
                    continue

            # 2. Metadata: Destination filter (case-insensitive substring or equality)
            if query.destination and chunk.destination:
                dest_filter = query.destination.strip().lower()
                chunk_dest = chunk.destination.strip().lower()
                if dest_filter not in chunk_dest and chunk_dest not in dest_filter:
                    continue

            # 3. Metadata: Country filter
            if query.country and chunk.country:
                if query.country.strip().lower() != chunk.country.strip().lower():
                    continue

            # 4. Metadata: Category filter
            if query.category and chunk.category:
                cat_filter = query.category.strip().lower()
                chunk_cat = chunk.category.strip().lower()
                if cat_filter != chunk_cat and cat_filter not in chunk_cat:
                    continue

            # 5. Metadata: Source Trust filter
            if query.source_trust and chunk.source_trust != query.source_trust:
                continue

            # 6. Semantic Cosine Similarity
            if chunk.embedding:
                similarity = BaseEmbeddingService.cosine_similarity(query_vec, chunk.embedding)
            else:
                similarity = 0.5  # Neutral fallback

            if similarity < query.min_similarity:
                continue

            scored_candidates.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    content=chunk.content,
                    similarity_score=round(similarity, 4),
                    source=chunk.source,
                    source_url=chunk.source_url,
                    source_trust=chunk.source_trust,
                    destination=chunk.destination,
                    country=chunk.country,
                    category=chunk.category,
                    metadata=chunk.metadata,
                    untrusted=True,
                )
            )

        # Sort descending by similarity score
        scored_candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        top_chunks = scored_candidates[: query.top_k]

        sources: List[str] = []
        for c in top_chunks:
            c_label = f"[{c.source_trust.value}] {c.title}"
            if c.source_url:
                c_label += f" ({c.source_url})"
            elif c.source:
                c_label += f" ({c.source})"
            if c_label not in sources:
                sources.append(c_label)

        top_score = top_chunks[0].similarity_score if top_chunks else 0.0

        return RAGRetrievalResult(
            query=query.query,
            destination=query.destination,
            results=top_chunks,
            total_chunks=len(top_chunks),
            top_score=top_score,
            sources=sources,
            mode="DEMO" if self.is_demo else "LIVE",
        )

    def _retrieve_live_supabase(self, query: RAGRetrievalQuery) -> RAGRetrievalResult:
        """Query live Supabase pgvector using the match_travel_documents RPC function."""
        client = self.supabase_svc.get_client()
        if not client:
            raise RuntimeError("Live Supabase client is not available")

        query_vec = self.embedding_service.embed_query(query.query)

        # Call PostgreSQL stored procedure
        rpc_params = {
            "query_embedding": query_vec,
            "match_count": query.top_k,
            "filter_destination": query.destination,
            "filter_country": query.country,
            "filter_category": query.category,
            "filter_user_id": query.user_id,
        }

        response = client.rpc("match_travel_documents", rpc_params).execute()
        rows = response.data or []

        chunks: List[RetrievedChunk] = []
        sources: List[str] = []

        for row in rows:
            sim = float(row.get("similarity", 0.0))
            if sim < query.min_similarity:
                continue

            trust = SourceTrustLevel(row.get("source_trust", "CURATED"))
            chunk = RetrievedChunk(
                chunk_id=row.get("chunk_id"),
                document_id=row.get("document_id"),
                title=row.get("title", "Curated Guide"),
                content=row.get("content", ""),
                similarity_score=round(sim, 4),
                source=row.get("source", "Supabase Travel Knowledge Base"),
                source_url=row.get("source_url"),
                source_trust=trust,
                destination=row.get("destination"),
                country=row.get("country"),
                category=row.get("category", "general"),
                metadata=row.get("metadata") or {},
                untrusted=True,
            )
            chunks.append(chunk)

            s_label = f"[{trust.value}] {chunk.title}"
            if chunk.source_url:
                s_label += f" ({chunk.source_url})"
            elif chunk.source:
                s_label += f" ({chunk.source})"
            if s_label not in sources:
                sources.append(s_label)

        top_score = chunks[0].similarity_score if chunks else 0.0

        return RAGRetrievalResult(
            query=query.query,
            destination=query.destination,
            results=chunks,
            total_chunks=len(chunks),
            top_score=top_score,
            sources=sources,
            mode="LIVE",
        )

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Return summary statistics of currently indexed knowledge for UI inspection."""
        chunks = self.mock_store.get_all_chunks()
        destinations = sorted(list({c.destination for c in chunks if c.destination}))
        categories = sorted(list({c.category for c in chunks if c.category}))
        doc_count = len({c.document_id for c in chunks})

        return {
            "total_documents": doc_count,
            "total_chunks": len(chunks),
            "destinations": destinations,
            "categories": categories,
            "embedding_model": self.embedding_service.model_name,
            "embedding_dimension": self.embedding_service.dimension,
            "mode": "DEMO" if self.is_demo else "LIVE",
        }


# Global singleton retriever instance
travel_knowledge_retriever = TravelKnowledgeRetriever()
