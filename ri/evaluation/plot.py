"""Bar-chart plots for P/R/F1 and timing."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def plot_metrics(results: list[dict[str, Any]], out_dir: Path | str) -> tuple[Path, Path]:
    """Write ``eval_precision_recall.png`` and ``eval_timing.png`` to ``out_dir``."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ids = [r["id"] for r in results]
    ps = [r["precision"] for r in results]
    rs = [r["recall"] for r in results]
    fs = [r["f1"] for r in results]
    ms = [r["ms"] for r in results]

    fig, ax = plt.subplots(figsize=(max(8, len(ids) * 1.2), 4))
    x = range(len(ids))
    w = 0.27
    ax.bar([i - w for i in x], ps, width=w, label="Precision")
    ax.bar(list(x), rs, width=w, label="Recall")
    ax.bar([i + w for i in x], fs, width=w, label="F1")
    ax.set_xticks(list(x))
    ax.set_xticklabels(ids)
    ax.set_ylim(0, 1.05)
    ax.set_title("Precision / Recall / F1 per query")
    ax.legend()
    pr_path = out / "eval_precision_recall.png"
    fig.tight_layout()
    fig.savefig(pr_path, dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(max(8, len(ids) * 1.2), 4))
    ax.bar(list(x), ms)
    ax.set_xticks(list(x))
    ax.set_xticklabels(ids)
    ax.set_title("Per-query latency (ms / run)")
    ax.set_ylabel("ms")
    tim_path = out / "eval_timing.png"
    fig.tight_layout()
    fig.savefig(tim_path, dpi=120)
    plt.close(fig)

    return pr_path, tim_path
