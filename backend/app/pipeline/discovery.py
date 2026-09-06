"""Activity embedding.

Prefers Sentence-BERT. When it is unavailable the service degrades to a
deterministic lexical embedding (hashed character n-grams) rather than to zero
vectors — zero vectors are not merely low quality, they make cosine distance
undefined and crash clustering outright.

The lexical fallback still groups obvious variants ("verify invoice vs PO" and
"Verify invoice against purchase order"), so the pipeline stays useful on a
machine without the 80MB model.
"""
from __future__ import annotations

import logging
import re

import numpy as np

logger = logging.getLogger(__name__)

_FALLBACK_DIM = 384
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _lexical_embedding(texts: list[str], dim: int = _FALLBACK_DIM) -> np.ndarray:
    """Hashed word + character-trigram vectors, L2-normalised.

    Deterministic across runs and processes (hashing uses a fixed algorithm,
    not Python's randomised ``hash()``), so clustering is reproducible.
    """
    vectors = np.zeros((len(texts), dim), dtype=np.float32)

    for row, text in enumerate(texts):
        lowered = (text or "").lower()
        features: list[str] = _TOKEN_RE.findall(lowered)
        squashed = " ".join(features)
        features += [squashed[i:i + 3] for i in range(max(len(squashed) - 2, 0))]

        for feat in features:
            # zlib.crc32 is stable across interpreter restarts, unlike hash().
            from zlib import crc32
            vectors[row, crc32(feat.encode()) % dim] += 1.0

        norm = np.linalg.norm(vectors[row])
        if norm > 0:
            vectors[row] /= norm
        else:
            # Empty/unusable label: park it on a unique axis so it is distinct
            # from every other vector but still non-zero.
            vectors[row, row % dim] = 1.0

    return vectors


class EmbeddingService:
    def __init__(self) -> None:
        self.model = None
        self.available = False
        try:
            from sentence_transformers import SentenceTransformer

            self._SentenceTransformer = SentenceTransformer
            self.available = True
        except ImportError:
            logger.warning(
                "sentence-transformers not installed; using deterministic "
                "lexical embeddings. Semantic grouping quality will be lower."
            )

    @property
    def backend(self) -> str:
        return "sentence-transformers" if self.available else "lexical-fallback"

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, _FALLBACK_DIM), dtype=np.float32)

        if not self.available:
            return _lexical_embedding(texts)

        if self.model is None:
            self.model = self._SentenceTransformer("all-MiniLM-L6-v2")

        return self.model.encode(texts, normalize_embeddings=True)


_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
