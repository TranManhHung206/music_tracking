"""
Package evals chua tap Golden Dataset va module danh gia hieu nang RAG.
"""

from .metrics import (
    compute_recall_at_k,
    compute_precision_at_k,
    compute_mrr,
    compute_abstention_accuracy,
)
from .runner import EvaluationRunner

__all__ = [
    "compute_recall_at_k",
    "compute_precision_at_k",
    "compute_mrr",
    "compute_abstention_accuracy",
    "EvaluationRunner",
]
