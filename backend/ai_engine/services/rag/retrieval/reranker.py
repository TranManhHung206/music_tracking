"""
Module Reranker tai xep hang do tuong quan cua cac ung vien Top-k.
Ho tro TermSemanticReranker (chuan xac, sieu nhe, khong can tai model nang) va CrossEncoder.
"""

import math
from typing import Any
from ..schemas import SearchHit
from ..vectorstore.bm25_store import CodeTokenizer, strip_accents

GENERIC_QUERY_WORDS = {
    "cơ", "co", "chế", "che", "sở", "so", "dữ", "du", "liệu", "lieu", "thuật", "thuat",
    "toán", "toan", "cách", "cach", "thức", "thuc", "hoạt", "hoat", "động", "dong",
    "như", "nhu", "thế", "the", "nào", "nao", "làm", "lam", "sao", "được", "duoc",
    "triển", "trien", "khai", "gì", "gi", "trong", "và", "va", "của", "cua", "cho",
    "các", "một", "những", "với", "vai", "trò", "ở", "tại", "về", "từ", "ra", "để"
}


class TermSemanticReranker:
    """
    Reranker tinh toan tuong quan sau giua cau hoi va doan ma nguon.
    Uu tien khop dinh danh (symbol match), ti le phu tu khoa va mat do xuat hien.
    """

    def __init__(self):
        self.tokenizer = CodeTokenizer()

    def rerank(self, query: str, hits: list[SearchHit], top_n: int = 5) -> list[SearchHit]:
        """Cham diem lai va tra ve top_n chunks tot nhat voi tinh da dang."""
        if not hits:
            return []

        all_tokens = self.tokenizer.tokenize(query)
        # Loc cac tu nghi van / tu thong thuong trong cau hoi de tap trung vao domain keywords
        query_tokens = [t for t in all_tokens if t not in GENERIC_QUERY_WORDS]
        if not query_tokens:
            query_tokens = all_tokens
        if not query_tokens:
            return hits[:top_n]

        unique_q_tokens = set(query_tokens)
        scored_hits: list[SearchHit] = []

        for hit in hits:
            chunk = hit.chunk
            meta = chunk.metadata
            chunk_text_lower = chunk.text.lower()
            symbol_lower = (meta.symbol or "").lower()
            path_lower = meta.path.lower()

            chunk_text_stripped = strip_accents(chunk_text_lower)
            symbol_stripped = strip_accents(symbol_lower)

            # 1. Tinh ti le phu tu khoa (Term Coverage)
            found_count = 0
            for t in unique_q_tokens:
                t_stripped = strip_accents(t)
                if (
                    t in chunk_text_lower
                    or t in symbol_lower
                    or t_stripped in chunk_text_stripped
                    or t_stripped in symbol_stripped
                ):
                    found_count += 1
            coverage = found_count / len(unique_q_tokens) if unique_q_tokens else 0.0

            # 2. Thuong diem neu khop chinh xac ten dinh danh (Symbol Match cho code hoac heading cu the)
            symbol_bonus = 0.0
            for t in unique_q_tokens:
                t_stripped = strip_accents(t)
                if len(t) >= 3 and (t in symbol_lower or t_stripped in symbol_stripped):
                    symbol_bonus += 0.25
                elif len(t) >= 4 and (t in path_lower or t_stripped in path_lower):
                    symbol_bonus += 0.15
            symbol_bonus = min(symbol_bonus, 0.4)

            # 3. Diem nen tu Dense va RRF
            base_dense = hit.dense_score or 0.0
            base_rrf = (hit.rrf_score or 0.0) * 30.0

            # Tong hop diem cuoi cung
            final_score = (coverage * 0.45) + symbol_bonus + (base_dense * 0.25) + (base_rrf * 0.15)
            hit.rerank_score = round(final_score, 4)
            scored_hits.append(hit)

        scored_hits.sort(key=lambda h: h.rerank_score or 0.0, reverse=True)

        # Ap dung co che Diversity: toi da 2 chunks cho cung 1 file de tranh crowd-out ma nguon
        diverse_hits: list[SearchHit] = []
        path_counts: dict[str, int] = {}
        for h in scored_hits:
            p = h.chunk.metadata.path
            if path_counts.get(p, 0) < 2:
                diverse_hits.append(h)
                path_counts[p] = path_counts.get(p, 0) + 1
            if len(diverse_hits) == top_n:
                break

        if len(diverse_hits) < top_n:
            seen_ids = {h.chunk.metadata.chunk_id for h in diverse_hits}
            for h in scored_hits:
                if h.chunk.metadata.chunk_id not in seen_ids:
                    diverse_hits.append(h)
                    seen_ids.add(h.chunk.metadata.chunk_id)
                if len(diverse_hits) == top_n:
                    break

        return diverse_hits


class CrossEncoderReranker:
    """Wrapper cho mo hinh Cross-Encoder neu nguoi dung cai dat sentence-transformers."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        self._fallback = TermSemanticReranker()

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except Exception:
                self._model = False

    def rerank(self, query: str, hits: list[SearchHit], top_n: int = 5) -> list[SearchHit]:
        """Tai xep hang bang CrossEncoder hoac fallback sang TermSemanticReranker."""
        self._load_model()
        if not self._model or self._model is False:
            return self._fallback.rerank(query, hits, top_n)

        try:
            pairs = [(query, h.chunk.text) for h in hits]
            scores = self._model.predict(pairs)
            for h, s in zip(hits, scores):
                h.rerank_score = float(s)
            hits.sort(key=lambda h: h.rerank_score or 0.0, reverse=True)
            return hits[:top_n]
        except Exception:
            return self._fallback.rerank(query, hits, top_n)
