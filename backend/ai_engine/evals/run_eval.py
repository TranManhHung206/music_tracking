"""
Script thuc thi danh gia Benchmark RAG tren tap Golden Dataset tu dong.
Chay doc lap tren moi truong Django de do luong cac chi so Recall, Precision, MRR va Latency.
"""

import os
import sys
from pathlib import Path

# Thiet lap PYTHONPATH va Django Settings
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from ai_engine.evals.runner import EvaluationRunner


def main():
    """Chay danh gia va in bang so sanh chi tiet."""
    print("=" * 70)
    print("BENCHMARK HE THONG RAG CODEBASE - GOLDEN DATASET (20 CAU HOI)")
    print("=" * 70)

    runner = EvaluationRunner()
    results = runner.run_full_benchmark()

    dense = results["baseline_dense"]
    cascade = results["full_cascade"]
    imp = results["improvement"]

    print("\nBANG SO SANH HIEU NANG TRUY XUAT (RETRIEVAL PERFORMANCE):")
    print("-" * 70)
    print(f"{'Chi so':<20} | {'Baseline Dense':<18} | {'Full Cascade':<18} | {'Tang truong':<10}")
    print("-" * 70)
    print(f"{'Recall@5':<20} | {dense['recall@k']:<18.4f} | {cascade['recall@k']:<18.4f} | +{imp['recall_lift_pct']}%")
    print(f"{'Precision@5':<20} | {dense['precision@k']:<18.4f} | {cascade['precision@k']:<18.4f} | +{imp['precision_lift_pct']}%")
    print(f"{'MRR':<20} | {dense['mrr']:<18.4f} | {cascade['mrr']:<18.4f} | +{imp['mrr_lift_pct']}%")
    print(f"{'Latency trung binh':<20} | {dense['avg_latency_ms']:<15.2f} ms | {cascade['avg_latency_ms']:<15.2f} ms | -")
    print(f"{'Abstention Acc.':<20} | {'-':<18} | {results['abstention_accuracy']:<18.4f} | -")
    print("-" * 70)
    print(f"Ket qua chi tiet da duoc ghi vao file: {runner.current_dir / 'eval_results.json'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
