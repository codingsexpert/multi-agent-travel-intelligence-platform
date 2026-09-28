"""Embedding service abstractions supporting OpenAI text-embedding-3 and deterministic Mock embeddings."""

from abc import ABC, abstractmethod
import hashlib
import math
import random
from typing import List, Optional
from config.settings import Settings, get_settings
from utils.exceptions import EmbeddingConfigurationError
from utils.logger import logger


class BaseEmbeddingService(ABC):
    """Abstract interface for generating vector embeddings."""

    def __init__(self, dimension: int = 1536, model_name: str = "text-embedding-3-small"):
        self.dimension = dimension
        self.model_name = model_name

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string into a normalized vector."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document strings into normalized vectors."""
        pass

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


class MockEmbeddingService(BaseEmbeddingService):
    """Deterministic, offline embedding service for DEMO_MODE and zero-cost unit testing.
    
    Generates normalized 1536-dimensional float vectors derived from text hashes.
    Two texts sharing words or concepts yield higher cosine similarity than unrelated texts.
    """

    def __init__(self, dimension: int = 1536, model_name: str = "text-embedding-3-small-mock"):
        super().__init__(dimension=dimension, model_name=model_name)
        self.provider = "mock"

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic unit-normalized pseudo-vector from text hash and word tokens."""
        clean_text = text.strip().lower()
        if not clean_text:
            # Return zero vector or neutral normalized vector
            val = 1.0 / math.sqrt(self.dimension)
            return [val] * self.dimension

        # Seed pseudo-random generator with text SHA-256 for deterministic reproducibility
        sha_int = int(hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(sha_int)

        # Base noise vector
        vec = [rng.gauss(0.0, 1.0) for _ in range(self.dimension)]

        # Add semantic token affinity: words modify specific dimension buckets
        tokens = [t for t in clean_text.split() if len(t) > 2]
        for token in tokens:
            token_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
            bucket = token_hash % self.dimension
            # Boost the token bucket and adjacent dimensions
            vec[bucket] += 2.5
            vec[(bucket + 7) % self.dimension] += 1.5

        # Normalize to unit length (L2 norm = 1.0)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]

        return vec

    def embed_query(self, text: str) -> List[float]:
        """Embed a single search query."""
        return self._generate_vector(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document texts."""
        return [self._generate_vector(t) for t in texts]


class OpenAIEmbeddingService(BaseEmbeddingService):
    """Production embedding service utilizing OpenAI text-embedding-3 API."""

    def __init__(self, settings: Optional[Settings] = None):
        cfg = settings or get_settings()
        dimension = cfg.embedding_dimension
        model_name = cfg.embedding_model
        super().__init__(dimension=dimension, model_name=model_name)
        self.settings = cfg
        self.provider = "openai"

        if not self.settings.openai_api_key or not self.settings.openai_api_key.get_secret_value():
            if not self.settings.demo_mode:
                raise EmbeddingConfigurationError(
                    message="Missing OPENAI_API_KEY required for live vector embedding generation.",
                    details={"model": self.model_name, "provider": self.provider},
                )

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector for search query using OpenAI API."""
        if not self.settings.has_llm_config:
            raise EmbeddingConfigurationError("OpenAI API credentials not configured.")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key.get_secret_value())
            response = client.embeddings.create(
                input=[text],
                model=self.model_name,
                dimensions=self.dimension,
            )
            embedding = response.data[0].embedding
            if len(embedding) != self.dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}"
                )
            return embedding
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for batch of document chunks using OpenAI API."""
        if not texts:
            return []

        if not self.settings.has_llm_config:
            raise EmbeddingConfigurationError("OpenAI API credentials not configured.")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key.get_secret_value())
            # Batch in chunks of 50
            results: List[List[float]] = []
            batch_size = 50
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                response = client.embeddings.create(
                    input=batch,
                    model=self.model_name,
                    dimensions=self.dimension,
                )
                for item in response.data:
                    results.append(item.embedding)
            return results
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            raise


def get_embedding_service(settings: Optional[Settings] = None) -> BaseEmbeddingService:
    """Factory creating appropriate embedding service based on runtime configuration."""
    cfg = settings or get_settings()

    # If demo mode is active or mock provider is explicitly set
    if cfg.demo_mode or cfg.embedding_provider.lower() == "mock":
        return MockEmbeddingService(
            dimension=cfg.embedding_dimension,
            model_name=f"{cfg.embedding_model}-mock",
        )

    # In live mode, verify credentials
    if not cfg.has_embedding_config:
        logger.warning("Live embedding credentials missing; falling back to MockEmbeddingService with DEMO marker.")
        return MockEmbeddingService(
            dimension=cfg.embedding_dimension,
            model_name=f"{cfg.embedding_model}-mock",
        )

    return OpenAIEmbeddingService(settings=cfg)
