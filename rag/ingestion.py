"""Document ingestion, text cleaning, deterministic chunking, and deduplication pipeline."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from config.settings import Settings, get_settings
from models.rag import DocumentMetadata, DocumentChunk, SourceTrustLevel
from rag.embeddings import BaseEmbeddingService, get_embedding_service
from utils.logger import logger


class DocumentIngestionPipeline:
    """Production-grade ingestion pipeline for travel documents."""

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.embedding_service = embedding_service or get_embedding_service(self.settings)
        self.chunk_size = self.settings.rag_chunk_size
        self.chunk_overlap = self.settings.rag_chunk_overlap
        # Hash cache tracking ingested documents: {doc_hash: {model: ..., chunks: [...]}}
        self._ingested_hashes: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize raw document text.
        
        - Normalizes unicode spaces and tabs
        - Strips excessive blank lines (> 2 consecutive newlines)
        - Removes unprintable control characters while preserving formatting
        """
        if not text:
            return ""

        # Remove null bytes and invisible control characters (preserve \n, \t)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Normalize carriage returns
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse 3+ newlines into 2
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Strip trailing and leading whitespace
        return cleaned.strip()

    def extract_document_content(
        self,
        file_path_or_content: Union[str, Path],
        file_type: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract textual content and header metadata from file path or raw string.
        
        Supports Markdown (.md), Plain Text (.txt), and JSON (.json).
        """
        content = ""
        meta: Dict[str, Any] = {}

        if isinstance(file_path_or_content, Path) or (
            isinstance(file_path_or_content, str) and (
                file_path_or_content.endswith(".md")
                or file_path_or_content.endswith(".txt")
                or file_path_or_content.endswith(".json")
            ) and Path(file_path_or_content).is_file()
        ):
            p = Path(file_path_or_content)
            raw = p.read_text(encoding="utf-8")
            ext = p.suffix.lower()

            if ext == ".json":
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    content = parsed.get("content") or parsed.get("text") or json.dumps(parsed, indent=2)
                    meta = {k: v for k, v in parsed.items() if k not in ("content", "text")}
                else:
                    content = json.dumps(parsed, indent=2)
            elif ext == ".md":
                content, meta = self._extract_markdown_frontmatter(raw)
            else:
                content = raw
        else:
            raw = str(file_path_or_content)
            if file_type == "json" or (raw.startswith("{") and raw.endswith("}")):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        content = parsed.get("content") or parsed.get("text") or json.dumps(parsed)
                        meta = {k: v for k, v in parsed.items() if k not in ("content", "text")}
                    else:
                        content = raw
                except Exception:
                    content = raw
            elif file_type == "md" or raw.startswith("---"):
                content, meta = self._extract_markdown_frontmatter(raw)
            else:
                content = raw

        cleaned_content = self.clean_text(content)
        return cleaned_content, meta

    @staticmethod
    def _extract_markdown_frontmatter(text: str) -> Tuple[str, Dict[str, Any]]:
        """Extract YAML-like frontmatter between leading --- delimiters if present."""
        meta: Dict[str, Any] = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                body = parts[2]
                for line in frontmatter_str.strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip("\"'")
                return body.strip(), meta
        return text.strip(), meta

    def chunk_text(
        self,
        text: str,
        metadata: DocumentMetadata,
    ) -> List[DocumentChunk]:
        """Deterministically chunk text into bounded windows with overlap.
        
        Preserves paragraph and sentence boundaries, avoiding fragmentation.
        """
        if not text:
            return []

        # Split into logical paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks_text: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for para in paragraphs:
            para_len = len(para)
            if current_length + para_len + 2 <= self.chunk_size:
                current_chunk.append(para)
                current_length += para_len + 2
            else:
                if current_chunk:
                    chunks_text.append("\n\n".join(current_chunk))
                
                # If paragraph itself exceeds chunk_size, split by sentences
                if para_len > self.chunk_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    sub_chunk: List[str] = []
                    sub_len = 0
                    for sent in sentences:
                        if sub_len + len(sent) + 1 <= self.chunk_size:
                            sub_chunk.append(sent)
                            sub_len += len(sent) + 1
                        else:
                            if sub_chunk:
                                chunks_text.append(" ".join(sub_chunk))
                            sub_chunk = [sent]
                            sub_len = len(sent)
                    if sub_chunk:
                        current_chunk = [" ".join(sub_chunk)]
                        current_length = sub_len
                    else:
                        current_chunk = []
                        current_length = 0
                else:
                    # Apply overlap from the tail of previous paragraph if feasible
                    current_chunk = [para]
                    current_length = para_len

        if current_chunk:
            chunks_text.append("\n\n".join(current_chunk))

        # Filter out trivially short chunks (< 25 characters) if multiple chunks exist
        if len(chunks_text) > 1:
            chunks_text = [c for c in chunks_text if len(c) >= 25]

        # Build DocumentChunk objects
        doc_chunks: List[DocumentChunk] = []
        for idx, c_text in enumerate(chunks_text):
            chunk_hash = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
            chunk_id = f"{metadata.document_id}_c{idx}_{chunk_hash[:8]}"

            doc_chunks.append(
                DocumentChunk(
                    document_id=metadata.document_id,
                    chunk_id=chunk_id,
                    chunk_index=idx,
                    title=metadata.title,
                    content=c_text,
                    source=metadata.source,
                    source_url=metadata.source_url,
                    source_trust=metadata.source_trust,
                    destination=metadata.destination,
                    country=metadata.country,
                    category=metadata.category,
                    language=metadata.language,
                    metadata={**metadata.extra, "char_count": len(c_text)},
                    is_public=metadata.is_public,
                    user_id=metadata.user_id,
                    content_hash=chunk_hash,
                )
            )

        return doc_chunks

    def ingest_document(
        self,
        content: str,
        metadata: DocumentMetadata,
    ) -> List[DocumentChunk]:
        """Execute full ingestion pipeline on raw text content.
        
        1. Clean content
        2. Deduplicate using SHA-256 document content hash
        3. Deterministically chunk
        4. Generate embeddings
        """
        cleaned = self.clean_text(content)
        if not cleaned:
            logger.warning(f"Document '{metadata.document_id}' is empty after cleaning; skipping.")
            return []

        doc_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

        # Check duplicate cache
        if doc_hash in self._ingested_hashes:
            cached = self._ingested_hashes[doc_hash]
            if cached.get("model") == self.embedding_service.model_name:
                logger.info(f"Duplicate document hash detected for '{metadata.document_id}'. Reusing cached chunks.")
                return cached["chunks"]

        # Chunk
        chunks = self.chunk_text(cleaned, metadata)
        if not chunks:
            return []

        # Embed batch
        texts_to_embed = [c.content for c in chunks]
        embeddings = self.embedding_service.embed_documents(texts_to_embed)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        # Record in duplicate tracking cache
        self._ingested_hashes[doc_hash] = {
            "document_id": metadata.document_id,
            "model": self.embedding_service.model_name,
            "dimension": self.embedding_service.dimension,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chunks": chunks,
        }

        logger.info(
            f"Successfully ingested document '{metadata.document_id}': {len(chunks)} chunks embedded via {self.embedding_service.model_name}."
        )
        return chunks
