"""FAISS vector index with sentence-transformers for local embedding."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np


@dataclass
class SearchResult:
    entity_id: str
    score: float


class EmbeddingIndex:
    def __init__(self, index_path: Path, model_name: str = "all-MiniLM-L6-v2"):
        self.index_path = index_path
        self._model_name = model_name
        self._model = None  # lazy load
        self._index: faiss.IndexFlatIP | None = None
        self._id_map: list[str] = []  # index position -> entity_id
        self._dimension: int | None = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _encode(self, text: str) -> np.ndarray:
        model = self._get_model()
        vec = model.encode([text], normalize_embeddings=True)
        return vec.astype(np.float32)

    def _ensure_index(self, dim: int):
        if self._index is None:
            self._dimension = dim
            self._index = faiss.IndexFlatIP(dim)  # inner product (cosine with normalized vecs)

    def add(self, entity_id: str, text: str) -> None:
        vec = self._encode(text)
        self._ensure_index(vec.shape[1])
        self._index.add(vec)
        self._id_map.append(entity_id)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self._index is None or self._index.ntotal == 0:
            return []
        vec = self._encode(query)
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._id_map):
                results.append(SearchResult(entity_id=self._id_map[idx], score=float(score)))
        return results

    def save(self) -> None:
        if self._index is not None:
            faiss.write_index(self._index, str(self.index_path))
            map_path = self.index_path.with_suffix(".idx2id.json")
            map_path.write_text(json.dumps(self._id_map))

    def load(self) -> None:
        if self.index_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            self._dimension = self._index.d
            map_path = self.index_path.with_suffix(".idx2id.json")
            if map_path.exists():
                self._id_map = json.loads(map_path.read_text())

    @property
    def count(self) -> int:
        return self._index.ntotal if self._index else 0
