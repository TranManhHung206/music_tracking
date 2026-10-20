"""
Dieu phoi Thac truy xuat (Retrieval Cascade) 4 buoc (Slide 40 SE373).
Ho tro cac che do chay de phuc vu danh gia va do luong.
"""

from enum import Enum
from typing import Any
from ..schemas import SearchHit
from ..vectorstore.chroma_store import ChromaStore
from ..vectorstore.bm25_store import BM25Store
from .hybrid_retriever import HybridRetriever
from .reranker import TermSemanticReranker
from ..config import get_rag_config


class PipelineMode(str, Enum):
    """Cac che do thuc thi cua pipeline truy xuat."""
    BASELINE_DENSE = "baseline_dense"
    HYBRID_RRF = "hybrid_rrf"
    FULL_CASCADE = "full_cascade"


class RetrievalCascade:
    """Dieu phoi toan bo luong truy xuat tu lay du den loc tinh va rerank."""

    def __init__(
        self,
        chroma_store: ChromaStore,
        bm25_store: BM25Store,
        reranker: TermSemanticReranker | None = None,
    ):
        self.chroma_store = chroma_store
        self.bm25_store = bm25_store
        self.hybrid_retriever = HybridRetriever(chroma_store, bm25_store)
        self.reranker = reranker or TermSemanticReranker()
        self.config = get_rag_config()

    def run(
        self,
        query: str,
        mode: PipelineMode = PipelineMode.FULL_CASCADE,
        final_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Thuc thi truy xuat theo che do da chon."""
        target_k = final_k or self.config.final_top_k

        # Che do 1: Chi dung Dense Vector (Baseline)
        if mode == PipelineMode.BASELINE_DENSE:
            return self.chroma_store.search_dense(query, top_k=target_k, filters=filters)

        # Che do 2: Hybrid RRF don thuan (khong qua Reranker)
        if mode == PipelineMode.HYBRID_RRF:
            return self.hybrid_retriever.search(
                query=query,
                overfetch_k=self.config.overfetch_top_k,
                rrf_k=self.config.rrf_k,
                top_n=target_k,
                filters=filters,
            )

        # Che do 3: Full Retrieval Cascade (Lay du Top 50 -> RRF Top 20 -> Reranker Top 5)
        candidate_hits = self.hybrid_retriever.search(
            query=query,
            overfetch_k=self.config.overfetch_top_k,
            rrf_k=self.config.rrf_k,
            top_n=self.config.rrf_top_k,
            filters=filters,
        )

        if not candidate_hits:
            return []

        return self.reranker.rerank(query, candidate_hits, top_n=target_k)

    def retrieve(self, query: str, **kwargs) -> list[SearchHit]:
        """Bi danh tien ich cho run()."""
        return self.run(query, **kwargs)
