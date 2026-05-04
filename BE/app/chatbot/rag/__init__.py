"""
RAG layer — FAISS semantic search cho product/category names.
Graceful fallback: nếu faiss/sentence-transformers chưa cài → skip.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Try import FAISS stack ────────────────────────────────────
try:
    import numpy as np
    import faiss
    from sentence_transformers import SentenceTransformer
    _FAISS_AVAILABLE = True
    logger.info("✅ FAISS + SentenceTransformers available")
except ImportError:
    _FAISS_AVAILABLE = False
    logger.info("⚠️  FAISS/SentenceTransformers not installed — semantic search disabled")


class SemanticIndex:
    """
    Index tên sản phẩm + danh mục để tìm kiếm ngữ nghĩa.
    Singleton per process.
    """

    def __init__(self) -> None:
        self._ready    = False
        self._names:   list[str] = []
        self._model    = None
        self._index    = None

    def build(self, names: list[str]) -> None:
        """Xây dựng FAISS index từ danh sách tên."""
        if not _FAISS_AVAILABLE or not names:
            return
        try:
            self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            embeddings  = self._model.encode(names, normalize_embeddings=True)
            dim         = embeddings.shape[1]

            self._index = faiss.IndexFlatIP(dim)   # Inner Product = cosine khi đã normalize
            self._index.add(embeddings.astype("float32"))
            self._names = names
            self._ready = True
            logger.info(f"✅ Semantic index built: {len(names)} items")
        except Exception as e:
            logger.warning(f"⚠️  Could not build semantic index: {e}")
            self._ready = False

    def search(self, query: str, top_k: int = 5, threshold: float = 0.45) -> list[str]:
        """
        Trả về tên sản phẩm/danh mục ngữ nghĩa tương tự query.
        threshold: cosine similarity tối thiểu (0–1).
        """
        if not self._ready or self._model is None or self._index is None:
            return []
        try:
            q_vec = self._model.encode([query], normalize_embeddings=True).astype("float32")
            scores, indices = self._index.search(q_vec, min(top_k, len(self._names)))
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and float(score) >= threshold:
                    results.append(self._names[idx])
            return results
        except Exception as e:
            logger.warning(f"Semantic search error: {e}")
            return []

    @property
    def ready(self) -> bool:
        return self._ready


# Singleton — dùng chung trong toàn app
_global_index: Optional[SemanticIndex] = None


def get_index() -> SemanticIndex:
    global _global_index
    if _global_index is None:
        _global_index = SemanticIndex()
    return _global_index


def rebuild_index(product_names: list[str], category_names: list[str]) -> None:
    """
    Gọi khi khởi động app hoặc sau khi thêm/xóa sản phẩm.
    """
    idx   = get_index()
    names = list(set(product_names + category_names))
    idx.build(names)


def semantic_search(query: str, top_k: int = 5) -> list[str]:
    return get_index().search(query, top_k=top_k)
