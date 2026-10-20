"""
Runner thuc thi danh gia thuc nghiem tren tap Golden Dataset 20 cau hoi.
Do luong Recall@5, Precision@5, MRR, Abstention Accuracy va Latency.
"""

import json
import time
from pathlib import Path
from typing import Any

from .metrics import (
    compute_recall_at_k,
    compute_precision_at_k,
    compute_mrr,
    compute_abstention_accuracy,
)
from ..services.rag.service import get_rag_service
from ..services.rag.retrieval.cascade import PipelineMode


class EvaluationRunner:
    """Dieu phoi benchmark he thong RAG tren tap Golden Dataset."""

    def __init__(self, dataset_path: Path | None = None):
        self.current_dir = Path(__file__).resolve().parent
        self.dataset_path = dataset_path or (self.current_dir / "golden_dataset.json")
        self.rag_service = get_rag_service()

    def load_dataset(self) -> list[dict[str, Any]]:
        """Nap tap du lieu vang 20 cau hoi tu JSON."""
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate_retrieval(
        self, mode: PipelineMode = PipelineMode.FULL_CASCADE, top_k: int = 5
    ) -> dict[str, Any]:
        """Danh gia hieu nang truy xuat (Retrieval Performance) cua cascade."""
        dataset = self.load_dataset()
        # Chi tinh Recall, Precision va MRR tren 14 cau hoi co dap an (Conceptual & Identifier)
        valid_samples = [item for item in dataset if not item.get("should_abstain")]

        recall_list = []
        precision_list = []
        mrr_list = []
        latencies = []

        item_results = []

        for item in valid_samples:
            q_id = item["id"]
            query = item["query"]
            exp_files = item.get("expected_files", [])
            exp_symbols = item.get("expected_symbols", [])

            t0 = time.time()
            hits = self.rag_service.cascade.run(
                query=query, mode=mode, final_k=top_k
            )
            lat_ms = (time.time() - t0) * 1000

            rec = compute_recall_at_k(hits, exp_files, exp_symbols)
            prec = compute_precision_at_k(hits, exp_files, exp_symbols)
            mrr_val = compute_mrr(hits, exp_files, exp_symbols)

            recall_list.append(rec)
            precision_list.append(prec)
            mrr_list.append(mrr_val)
            latencies.append(lat_ms)

            item_results.append({
                "id": q_id,
                "category": item["category"],
                "query": query,
                "recall@k": rec,
                "precision@k": prec,
                "mrr": mrr_val,
                "latency_ms": round(lat_ms, 2),
                "top_hit_path": hits[0].chunk.metadata.path if hits else None,
                "top_hit_symbol": hits[0].chunk.metadata.symbol if hits else None,
            })

        avg_recall = round(sum(recall_list) / len(recall_list), 4) if recall_list else 0.0
        avg_precision = round(sum(precision_list) / len(precision_list), 4) if precision_list else 0.0
        avg_mrr = round(sum(mrr_list) / len(mrr_list), 4) if mrr_list else 0.0
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

        return {
            "mode": mode.value,
            "total_samples": len(valid_samples),
            "recall@k": avg_recall,
            "precision@k": avg_precision,
            "mrr": avg_mrr,
            "avg_latency_ms": avg_latency,
            "details": item_results,
        }

    def run_full_benchmark(self) -> dict[str, Any]:
        """Chay benchmark so sanh Baseline Dense vs Full Cascade tren tap Golden Dataset."""
        self.rag_service.ensure_indexed()

        res_dense = self.evaluate_retrieval(mode=PipelineMode.BASELINE_DENSE)
        res_cascade = self.evaluate_retrieval(mode=PipelineMode.FULL_CASCADE)

        # Danh gia 6 cau hoi trick de kiem tra Escape Hatch
        dataset = self.load_dataset()
        trick_samples = [item for item in dataset if item.get("should_abstain")]
        abstention_scores = []

        for item in trick_samples:
            # Truy van qua service de kiem tra do nhan dien Escape Hatch
            response = self.rag_service.query(item["query"], use_cache=False)
            acc = compute_abstention_accuracy(response.answer, should_abstain=True)
            abstention_scores.append(acc)

        avg_abstention = (
            round(sum(abstention_scores) / len(abstention_scores), 4)
            if abstention_scores
            else 1.0
        )

        comparison = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "baseline_dense": res_dense,
            "full_cascade": res_cascade,
            "abstention_accuracy": avg_abstention,
            "improvement": {
                "recall_lift_pct": round(
                    ((res_cascade["recall@k"] - res_dense["recall@k"]) / max(res_dense["recall@k"], 0.001)) * 100, 2
                ),
                "precision_lift_pct": round(
                    ((res_cascade["precision@k"] - res_dense["precision@k"]) / max(res_dense["precision@k"], 0.001)) * 100, 2
                ),
                "mrr_lift_pct": round(
                    ((res_cascade["mrr"] - res_dense["mrr"]) / max(res_dense["mrr"], 0.001)) * 100, 2
                ),
            },
        }

        # Luu ket qua ra file json
        out_file = self.current_dir / "eval_results.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)

        return comparison
