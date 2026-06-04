"""Generate every paper figure from the committed benchmark result JSON.

No figure is drawn by hand: each plot is produced from
``benchmarks/moc_rag_benchmark/results/<embedder>/{results,variants}.json`` (and
the architecture diagram from matplotlib primitives). Figures are written as both
PDF (for LaTeX) and SVG (for web/README reuse).

    python docs/paper/latex/scripts/make_paper_figures.py [--embedder st]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
RESULTS = ROOT / "benchmarks" / "moc_rag_benchmark" / "results"
FIGDIR = Path(__file__).resolve().parents[1] / "figures"

# Consistent palette: flat baselines greyscale-ish, MoC variants highlighted.
FLAT = "#9aa0a6"
MOC = "#1a73e8"
MOC2 = "#0b3d91"
ACCENT = "#d93025"


def _load(embedder: str):
    res = json.loads((RESULTS / embedder / "results.json").read_text())
    var = json.loads((RESULTS / embedder / "variants.json").read_text())
    return res, var


def _save(fig, name: str):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg"):
        fig.savefig(FIGDIR / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    print(f"  figures/{name}.pdf  figures/{name}.svg")


def _is_moc(name: str) -> bool:
    return name.startswith("moc_rag")


def _colors(names):
    return [MOC if _is_moc(n) else FLAT for n in names]


# --------------------------------------------------------------------------- #
def fig_recall_by_query_type(var):
    """THE key plot: recall across keyword/paraphrased/adversarial per method."""
    cats = var["categories"]
    methods = var["order"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(cats))
    width = 0.9 / len(methods)
    for i, m in enumerate(methods):
        vals = [var["results"][m][c]["recall_at_k"] * 100 for c in cats]
        off = [xi + i * width - 0.45 + width / 2 for xi in x]
        ax.bar(off, vals, width, label=m,
               color=MOC if _is_moc(m) else FLAT,
               edgecolor="white", linewidth=0.4,
               hatch="//" if m == "bm25_rag" else None)
    ax.set_xticks(list(x))
    ax.set_xticklabels([c.capitalize() for c in cats])
    ax.set_ylabel("Recall@8 (%)")
    ax.set_title("Recall by query type — BM25 collapses on adversarial; MoC-RAG holds")
    ax.set_ylim(0, 105)
    ax.legend(ncol=3, fontsize=7, loc="lower left")
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "recall_by_query_type")


def fig_adversarial_recall_drop(var):
    cats = var["categories"]
    methods = var["order"]
    drops = [(var["results"][m][cats[-1]]["recall_at_k"]
              - var["results"][m][cats[0]]["recall_at_k"]) * 100 for m in methods]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(methods, drops, color=_colors(methods), edgecolor="white")
    for i, d in enumerate(drops):
        ax.text(d - 1 if d < 0 else d + 0.5, i, f"{d:+.0f}", va="center",
                ha="right" if d < 0 else "left", fontsize=8)
    ax.set_xlabel("Recall@8 change, keyword → adversarial (points)")
    ax.set_title("Robustness to adversarial lexical shift (closer to 0 = more robust)")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.grid(axis="x", alpha=0.3)
    _save(fig, "adversarial_recall_drop")


def fig_hard_distractors(var):
    """Hard distractors per method on the adversarial split (lower is better)."""
    cat = var["categories"][-1]
    methods = var["order"]
    vals = [var["results"][m][cat]["hard_distractors"] for m in methods]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(methods, vals, color=_colors(methods), edgecolor="white")
    ax.set_ylabel(f"Hard distractors in packs ({cat} split)")
    ax.set_title("Harmful context packed — MoC-RAG carries ~half the dense family")
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods, rotation=30, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "hard_distractors")


def fig_context_efficiency(res):
    methods = res["order"]
    vals = [res["results"][m].get("context_efficiency", 0.0) for m in methods]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(methods, vals, color=_colors(methods), edgecolor="white")
    ax.set_ylabel("Context efficiency  (Recall@K per 1k tokens)")
    ax.set_title("Context efficiency by method (mixed test split)")
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods, rotation=30, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "context_efficiency")


def fig_routing_accuracy(res):
    methods = [m for m in res["order"]
               if res["results"][m].get("routing_accuracy") is not None]
    vals = [res["results"][m]["routing_accuracy"] * 100 for m in methods]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar(methods, vals, color=[MOC2 if v >= 95 else MOC for v in vals],
           edgecolor="white")
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_ylabel("Expert routing accuracy (%)")
    ax.set_title("Routing accuracy by MoC-RAG variant")
    ax.set_ylim(0, 108)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "routing_accuracy")


def fig_recall_vs_distractors(var):
    """Pareto: adversarial recall (↑) vs hard distractors (↓)."""
    cat = var["categories"][-1]
    methods = var["order"]
    fig, ax = plt.subplots(figsize=(7, 5))
    for m in methods:
        r = var["results"][m][cat]["recall_at_k"] * 100
        d = var["results"][m][cat]["hard_distractors"]
        moc = _is_moc(m)
        ax.scatter(d, r, s=90, color=MOC if moc else FLAT,
                   marker="o" if moc else "s", zorder=3,
                   edgecolor="black", linewidth=0.4)
        ax.annotate(m, (d, r), textcoords="offset points", xytext=(6, 4),
                    fontsize=7, color=MOC2 if moc else "#5f6368")
    ax.set_xlabel(f"Hard distractors ({cat}) — lower is better →")
    ax.invert_xaxis()
    ax.set_ylabel(f"Recall@8 ({cat}) — higher is better ↑")
    ax.set_title("Pareto front: adversarial recall vs harmful context\n"
                 "(top-right is best; MoC-RAG dominates the dense family)")
    ax.grid(alpha=0.3)
    _save(fig, "recall_vs_distractors")


def fig_architecture(_=None):
    """MoC-RAG architecture, drawn from matplotlib primitives (not hand-art)."""
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    stages = [("Query", 0.7), ("Hybrid\nRouter", 2.4), ("Typed\nExperts", 4.1),
              ("Hybrid\nRetrieval", 5.8), ("Rerank", 7.3),
              ("Budgeted\nPack", 8.7)]
    for label, cx in stages:
        box = FancyBboxPatch((cx - 0.62, 1.2), 1.24, 0.8,
                             boxstyle="round,pad=0.04,rounding_size=0.08",
                             linewidth=1.2, edgecolor=MOC2,
                             facecolor="#e8f0fe")
        ax.add_patch(box)
        ax.text(cx, 1.6, label, ha="center", va="center", fontsize=8.5)
    for (_, x0), (_, x1) in zip(stages, stages[1:]):
        ax.add_patch(FancyArrowPatch((x0 + 0.62, 1.6), (x1 - 0.62, 1.6),
                                     arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.1, color="#5f6368"))
    # expert chips under the router/experts stage
    experts = ["session", "profile", "semantic", "episodic", "document", "policy",
               "decision", "tool"]
    for i, e in enumerate(experts):
        cx = 3.0 + (i % 4) * 0.95
        cy = 0.45 - (i // 4) * 0.42
        ax.add_patch(FancyBboxPatch((cx - 0.42, cy - 0.13), 0.84, 0.26,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    linewidth=0.6, edgecolor=MOC,
                                    facecolor="white"))
        ax.text(cx, cy, e, ha="center", va="center", fontsize=6)
    ax.text(8.7, 0.55, "explainable\ninspect()", ha="center", va="center",
            fontsize=7.5, color=ACCENT)
    ax.add_patch(FancyArrowPatch((8.7, 1.18), (8.7, 0.75), arrowstyle="-|>",
                                 mutation_scale=10, color=ACCENT, linewidth=1.0))
    ax.set_title("MoC-RAG: route typed context experts before retrieving",
                 fontsize=10)
    _save(fig, "architecture")


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--embedder", default="st", help="results subdir (st | hashing)")
    args = p.parse_args(argv)
    res, var = _load(args.embedder)
    print(f"Generating figures from results/{args.embedder}/ ->")
    fig_architecture()
    fig_recall_by_query_type(var)
    fig_adversarial_recall_drop(var)
    fig_hard_distractors(var)
    fig_context_efficiency(res)
    fig_routing_accuracy(res)
    fig_recall_vs_distractors(var)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
