"""
Module tinh toan cac chi so danh gia (Evaluation Metrics) cho RAG.
Tuan thu cac tieu chi do luong theo Slide 52-54 SE373:
Recall@k, Precision@k, MRR, Abstention Accuracy, va Citation Accuracy.
"""

from ..services.rag.schemas import SearchHit
from ..services.rag.grounding.prompt_builder import ESCAPE_HATCH_PHRASE


def is_hit_match(
    hit: SearchHit, expected_files: list[str], expected_symbols: list[str]
) -> bool:
    """Kiem tra xem mot SearchHit co trung voi file hoac symbol ky vong hay khong."""
    path = hit.chunk.metadata.path.replace("\\", "/")
    for exp_file in expected_files:
        if exp_file in path or path in exp_file:
            return True

    symbol = (hit.chunk.metadata.symbol or "").lower()
    for exp_sym in expected_symbols:
        if exp_sym.lower() in symbol or symbol in exp_sym.lower():
            return True

    return False


def compute_recall_at_k(
    hits: list[SearchHit], expected_files: list[str], expected_symbols: list[str]
) -> float:
    """Tinh Recall@k: 1.0 neu tim thay it nhat 1 chunk dung trong top-k, nguoc lai 0.0."""
    if not expected_files and not expected_symbols:
        return 1.0

    for hit in hits:
        if is_hit_match(hit, expected_files, expected_symbols):
            return 1.0
    return 0.0


def compute_precision_at_k(
    hits: list[SearchHit], expected_files: list[str], expected_symbols: list[str]
) -> float:
    """Tinh Precision@k: Ti le so chunks dung tren tong so chunks lay ve."""
    if not hits:
        return 0.0
    if not expected_files and not expected_symbols:
        return 0.0

    match_count = sum(1 for h in hits if is_hit_match(h, expected_files, expected_symbols))
    return round(match_count / len(hits), 4)


def compute_mrr(
    hits: list[SearchHit], expected_files: list[str], expected_symbols: list[str]
) -> float:
    """Tinh Mean Reciprocal Rank (MRR): 1 / thu_hang cua chunk dung dau tien."""
    if not expected_files and not expected_symbols:
        return 1.0

    for rank, hit in enumerate(hits, start=1):
        if is_hit_match(hit, expected_files, expected_symbols):
            return round(1.0 / rank, 4)
    return 0.0


def compute_abstention_accuracy(answer: str, should_abstain: bool) -> float:
    """
    Tinh Abstention Accuracy (Slide 52 & 54):
    Neu cau hoi ngoai le/khong co dap an, he thong phai tu choi dung (Escape Hatch).
    """
    is_abstain = ESCAPE_HATCH_PHRASE.lower() in answer.lower()
    if should_abstain:
        return 1.0 if is_abstain else 0.0
    else:
        return 1.0 if not is_abstain else 0.0
