"""Precision / Recall / F1 / timing for the golden set."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ri.evaluation.golden_set import GROUND_TRUTH
from ri.retrieval.engine import SearchService


def precision_recall_f1(retrieved: set[str], relevant: set[str]) -> tuple[float, float, float]:
    if not retrieved and not relevant:
        return 1.0, 1.0, 1.0
    if not retrieved:
        return 0.0, 0.0, 0.0
    if not relevant:
        return 0.0, 0.0, 0.0
    tp = len(retrieved & relevant)
    p = tp / len(retrieved)
    r = tp / len(relevant)
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f1


def time_query(svc: SearchService, query: str, runs: int = 10) -> float:
    """Average ms per run."""
    start = time.perf_counter()
    for _ in range(runs):
        svc.run(query)
    elapsed = (time.perf_counter() - start) / runs
    return elapsed * 1000.0


def run_eval(report_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Run the full golden-set evaluation; return per-query results."""
    svc = SearchService()
    results: list[dict[str, Any]] = []
    sum_p = sum_r = sum_f = 0.0
    print()
    print("=" * 78)
    print(f"{'ID':<5} {'Requête':<46} {'P':>6} {'R':>6} {'F1':>6} {'ms':>7}")
    print("-" * 78)
    try:
        for entry in GROUND_TRUTH:
            docs = svc.run(entry["query"])
            retrieved = {d["article"] for d in docs}
            relevant = entry["relevant_articles"]
            p, r, f1 = precision_recall_f1(retrieved, relevant)
            ms = time_query(svc, entry["query"], runs=10)
            results.append({
                "id": entry["id"], "query": entry["query"],
                "precision": p, "recall": r, "f1": f1, "ms": ms,
                "retrieved": sorted(retrieved), "relevant": sorted(relevant),
            })
            sum_p += p
            sum_r += r
            sum_f += f1
            label = entry["query"][:42] + ("..." if len(entry["query"]) > 42 else "")
            print(f"{entry['id']:<5} {label:<46} {p:6.3f} {r:6.3f} {f1:6.3f} {ms:7.1f}")
        n = len(GROUND_TRUTH)
        print("=" * 78)
        print(f"{'Moy.':<5} {' ':<46} {sum_p/n:6.3f} {sum_r/n:6.3f} {sum_f/n:6.3f}")
    finally:
        svc.close()
    if report_path:
        Path(report_path).write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return results
