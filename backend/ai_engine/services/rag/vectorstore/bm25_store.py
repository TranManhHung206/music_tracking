"""
Sparse Store Wrapper su dung rank_bm25 (BM25Plus).
Tich hop CodeTokenizer chuyen biet cho ma nguon va tai lieu ky thuat.
"""

import re
import pickle
import logging
import unicodedata
from pathlib import Path
from typing import Any
from rank_bm25 import BM25Plus
from ..schemas import CodeChunk, SearchHit
from ..config import get_rag_config

logger = logging.getLogger(__name__)

VIETNAMESE_STOP_WORDS = {
    "va", "và", "trong", "cua", "của", "duoc", "được", "voi", "với", "cho",
    "cac", "các", "mot", "một", "nhung", "những", "nhu", "như", "the", "thế",
    "nao", "nào", "la", "là", "gi", "gì", "co", "có", "su", "sử", "dung", "dụng",
    "theo", "nay", "này", "do", "đó", "khi", "de", "để", "sao", "ra", "o", "ở",
    "tai", "tại", "ve", "về", "tu", "từ", "hay", "hoac", "hoặc", "boi", "bởi",
    "tren", "trên", "duoi", "dưới", "nen", "nên", "thi", "thì", "mà",
    "den", "đến", "roi", "rồi", "lai", "lại", "qua", "se", "sẽ", "da", "đã",
}


def strip_accents(text: str) -> str:
    """Loai bo dau tieng Viet de dong bo tu khoa khong dau va co dau."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    ).replace("đ", "d").replace("Đ", "D")


class CodeTokenizer:
    """Bo phan tach tu chuyen biet cho ma nguon: tach snake_case, camelCase va chuan hoa tieng Viet."""

    def __init__(self):
        # Tach cac ky tu dac biet, dau cham cau
        self.split_punct = re.compile(r"[\s\.\(\)\[\]\{\}:;,+\-*/=<>!&|?\"'`~@#%^\\/]+")
        # Tach camelCase hoac PascalCase
        self.camel_case = re.compile(r"([a-z0-9])([A-Z])")

    def tokenize(self, text: str) -> list[str]:
        """Tach van ban thanh danh sach token lowercased kem bien the khong dau."""
        expanded = self.camel_case.sub(r"\1 \2", text)
        raw_tokens = self.split_punct.split(expanded)

        tokens: list[str] = []
        for t in raw_tokens:
            cleaned = t.strip().lower()
            if len(cleaned) < 2 or cleaned in VIETNAMESE_STOP_WORDS:
                continue

            tokens.append(cleaned)

            # Bo sung phien ban bo dau neu la tieng Viet co dau
            stripped = strip_accents(cleaned)
            if stripped != cleaned and len(stripped) >= 2 and stripped not in VIETNAMESE_STOP_WORDS:
                tokens.append(stripped)

            # Neu token co chua dau gach duoi, tach tiep thanh phan tu con
            if "_" in cleaned:
                sub_parts = [p for p in cleaned.split("_") if len(p) >= 2 and p not in VIETNAMESE_STOP_WORDS]
                tokens.extend(sub_parts)
                for sp in sub_parts:
                    sp_stripped = strip_accents(sp)
                    if sp_stripped != sp and len(sp_stripped) >= 2 and sp_stripped not in VIETNAMESE_STOP_WORDS:
                        tokens.append(sp_stripped)

        return tokens


class BM25Store:
    """Lop dieu phoi tim kiem tu khoa BM25Plus voi co che Idempotent."""

    def __init__(self, persist_path: Path | None = None):
        config = get_rag_config()
        self.persist_path = persist_path or config.bm25_persist_path
        self.tokenizer = CodeTokenizer()
        self.chunks: list[CodeChunk] = []
        self.tokenized_corpus: list[list[str]] = []
        self.bm25_model: BM25Plus | None = None

    def upsert_file_idempotent(self, path: str, chunks: list[CodeChunk]) -> None:
        """Cap nhat chunks cho 1 file duy nhat va rebuild index."""
        self.chunks = [c for c in self.chunks if c.metadata.path != path]
        self.chunks.extend(chunks)
        self._rebuild_index()

    def upsert_chunks(self, chunks: list[CodeChunk]) -> None:
        """Cap nhat danh sach nhieu chunks va rebuild index 1 lan duy nhat."""
        if not chunks:
            return

        paths_to_update = {c.metadata.path for c in chunks}
        self.chunks = [c for c in self.chunks if c.metadata.path not in paths_to_update]
        self.chunks.extend(chunks)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Xay dung lai chi muc BM25Plus tu danh sach chunks hien tai."""
        if not self.chunks:
            self.tokenized_corpus = []
            self.bm25_model = None
            return

        self.tokenized_corpus = [
            self.tokenizer.tokenize(f"{c.metadata.symbol or ''} {c.metadata.path} {c.text}")
            for c in self.chunks
        ]
        self.bm25_model = BM25Plus(self.tokenized_corpus)

    def search_sparse(
        self, query: str, top_k: int = 50, filters: dict[str, Any] | None = None
    ) -> list[SearchHit]:
        """Truy xuat sparse tu khoa bang BM25Plus."""
        if not self.bm25_model or not self.chunks:
            return []

        tokens = self.tokenizer.tokenize(query)
        if not tokens:
            return []

        scores = self.bm25_model.get_scores(tokens)

        # Loc theo dieu kien neu co
        candidate_indices = range(len(self.chunks))
        if filters:
            filtered_indices = []
            for i in candidate_indices:
                meta_dict = self.chunks[i].metadata.to_dict()
                match = True
                for k, v in filters.items():
                    if meta_dict.get(k) != v:
                        match = False
                        break
                if match:
                    filtered_indices.append(i)
            candidate_indices = filtered_indices

        scored_pairs = [(i, float(scores[i])) for i in candidate_indices if scores[i] > 0]
        scored_pairs.sort(key=lambda x: x[1], reverse=True)

        hits: list[SearchHit] = []
        for idx, score in scored_pairs[:top_k]:
            hits.append(SearchHit(chunk=self.chunks[idx], sparse_score=score))

        return hits

    def count(self) -> int:
        """Tra ve tong so chunks hien co."""
        return len(self.chunks)

    def persist(self) -> None:
        """Luu index va chunks ra file tren dia."""
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, "wb") as f:
                pickle.dump(self.chunks, f)
        except Exception as e:
            logger.warning("Khong the luu BM25 store ra dia: %s", e)

    def load(self) -> bool:
        """Doc chunks tu file tren dia va khoi phuc index."""
        if not self.persist_path.exists():
            return False
        try:
            with open(self.persist_path, "rb") as f:
                self.chunks = pickle.load(f)
            self._rebuild_index()
            return True
        except Exception as e:
            logger.warning("Loi nap BM25 store tu dia: %s", e)
            return False

    def clear(self) -> None:
        """Xoa trang store."""
        self.chunks = []
        self.tokenized_corpus = []
        self.bm25_model = None
        if self.persist_path.exists():
            try:
                self.persist_path.unlink()
            except Exception:
                pass
