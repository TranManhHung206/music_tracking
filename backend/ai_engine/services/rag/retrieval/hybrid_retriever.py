"""
Hybrid Search Retriever ket hop Dense Vector va Sparse BM25Plus.
Ap dung thuat toan Reciprocal Rank Fusion (RRF) voi hang so k=60.
"""

from typing import Any
from ..schemas import SearchHit
from ..vectorstore.chroma_store import ChromaStore
from ..vectorstore.bm25_store import BM25Store
from ..config import get_rag_config


def rrf(rank_lists: list[list[SearchHit]], k: int = 60, top_n: int = 20) -> list[SearchHit]:
    """
    Thuat toan Reciprocal Rank Fusion (RRF) theo Slide 34-36 SE373.
    Hop nhat thu hang cac chunks tu nhieu nguon truy xuat (Dense, BM25).
    """
    scores: dict[str, float] = {}
    hit_lookup: dict[str, SearchHit] = {}

    for ranked in rank_lists:
        for rank, hit in enumerate(ranked, start=1):
            chunk_id = hit.chunk.metadata.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

            if chunk_id not in hit_lookup:
                hit_lookup[chunk_id] = hit
            else:
                # Cap nhat diem tu cac store
                if hit.dense_score is not None:
                    hit_lookup[chunk_id].dense_score = hit.dense_score
                if hit.sparse_score is not None:
                    hit_lookup[chunk_id].sparse_score = hit.sparse_score

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_n]

    result: list[SearchHit] = []
    for c_id in sorted_ids:
        hit = hit_lookup[c_id]
        hit.rrf_score = scores[c_id]
        result.append(hit)

    return result


class HybridRetriever:
    """Dieu phoi truy xuat lai song song Dense va Sparse."""

    def __init__(self, chroma_store: ChromaStore, bm25_store: BM25Store):
        self.chroma_store = chroma_store
        self.bm25_store = bm25_store
        self.config = get_rag_config()

    def search(
        self,
        query: str,
        overfetch_k: int = 50,
        rrf_k: int = 60,
        top_n: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Thuc hien tim kiem Dense va Sparse roi hop nhat bang RRF."""
        dense_hits = self.chroma_store.search_dense(query, top_k=overfetch_k, filters=filters)
        sparse_hits = self.bm25_store.search_sparse(query, top_k=overfetch_k, filters=filters)

        # Neu chi co mot nguon co ket qua, tra ve truc tiep
        if not dense_hits and not sparse_hits:
            return []
        if not dense_hits:
            return sparse_hits[:top_n]
        if not sparse_hits:
            return dense_hits[:top_n]

        return rrf([dense_hits, sparse_hits], k=rrf_k, top_n=top_n)
