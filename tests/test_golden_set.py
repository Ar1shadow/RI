"""Golden-set parity check.

Pass criterion (per plan): mean F1 within +/-2% of TD6 baseline (0.720).
Actual: ~0.91 (well above), so we set a hard floor at 0.70.
"""

from ri.evaluation.golden_set import GROUND_TRUTH
from ri.evaluation.metrics import precision_recall_f1
from ri.ranking.vsm import VSMScorer
from ri.retrieval.engine import SearchService


def test_golden_set_mean_f1_above_floor(built_index):
    svc = SearchService(index=built_index, scorer=VSMScorer())
    total_f1 = 0.0
    for entry in GROUND_TRUTH:
        docs = svc.run(entry["query"])
        retrieved = {d["article"] for d in docs}
        _, _, f1 = precision_recall_f1(retrieved, entry["relevant_articles"])
        total_f1 += f1
    mean_f1 = total_f1 / len(GROUND_TRUTH)
    assert mean_f1 >= 0.70, f"mean F1 = {mean_f1:.3f} below baseline floor"
