"""Optional, local dense retrieval for Gulshan AI.

FastEmbed uses ONNX instead of PyTorch and downloads the selected model to the
local user cache on first use. No portfolio content is sent to an embedding API.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Iterable


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class SemanticMatch:
    document_id: str
    similarity: float


def _unit(vector: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in vector)
    length = math.sqrt(sum(value * value for value in values))
    return tuple(value / length for value in values) if length else values


class LocalSemanticIndex:
    """Small in-memory cosine index over the approved portfolio documents.

    Cache embeddings across file refreshes within the same Python process. Text
    changes are re-embedded, removed documents disappear from the active index.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL, model=None):
        if model is None:
            from fastembed import TextEmbedding
            model = TextEmbedding(model_name=model_name)
        self.model = model
        self.model_name = model_name
        self._cached: dict[str, tuple[str, tuple[float, ...]]] = {}
        self.vectors: dict[str, tuple[float, ...]] = {}

    def build(self, documents: list) -> None:
        current: dict[str, tuple[float, ...]] = {}
        changed: list[tuple[str, str, str]] = []
        for document in documents:
            # Title assists semantically ambiguous short descriptions. The CV
            # already arrives as separately sourced, small page-level chunks.
            content = f"{document.title}. {document.text[:1800]}"
            signature = hashlib.sha256(content.encode("utf-8")).hexdigest()
            cached = self._cached.get(document.id)
            if cached and cached[0] == signature:
                current[document.id] = cached[1]
            else:
                changed.append((document.id, signature, content))

        if changed:
            encoded = list(self.model.embed([item[2] for item in changed]))
            if len(encoded) != len(changed):
                raise RuntimeError("Embedding model returned the wrong vector count")
            for (document_id, signature, _), embedding in zip(changed, encoded):
                values = _unit(embedding)
                if not values or not any(values):
                    raise RuntimeError("Embedding model returned an empty embedding")
                self._cached[document_id] = (signature, values)
                current[document_id] = values

        # Discard old documents, including their cached embeddings.
        self._cached = {document_id: self._cached[document_id] for document_id in current}
        self.vectors = current

    def search(self, query: str, eligible_ids: set[str] | None = None,
               limit: int = 15, min_similarity: float = 0.24) -> list[SemanticMatch]:
        if not self.vectors or not query.strip():
            return []
        encoded = list(self.model.embed([query]))
        if len(encoded) != 1:
            return []
        query_vector = _unit(encoded[0])
        ranked: list[SemanticMatch] = []
        for document_id, vector in self.vectors.items():
            if eligible_ids is not None and document_id not in eligible_ids:
                continue
            if len(query_vector) != len(vector):
                continue
            cosine = sum(a * b for a, b in zip(query_vector, vector))
            if cosine >= min_similarity:
                ranked.append(SemanticMatch(document_id, cosine))
        return sorted(ranked, key=lambda item: (-item.similarity, item.document_id))[:limit]
