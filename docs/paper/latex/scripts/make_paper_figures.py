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
# Embed real (Type-42/TrueType) fonts so PDF text stays selectable/searchable and
# copy-paste extracts correctly; keep SVG text as text rather than outlined paths.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["svg.fonttype"] = "none"
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

# Short, figure-friendly method labels (full names live in the captions).
SHORT = {
    "bm25_rag": "BM25", "dense_rag": "Dense", "hybrid_rag": "Hybrid",
    "metadata_rag": "Metadata", "reranked_rag": "Reranked",
    "moc_rag_e1": "MoC-1", "moc_rag_e2": "MoC-2", "moc_rag_e3": "MoC-3",
    "moc_rag_all": "MoC-All",
}


def _short(name: str) -> str:
    return SHORT.get(name, name)


def _load(embedder: str):
    res = json.loads((RESULTS / embedder / "results.json").read_text())
    var = json.loads((RESULTS / embedder / "variants.json").read_text())
    return res, var


def _save(fig, name: str):
    FIGDIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg"):
        fig.savefig(FIGDIR / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.12)
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
        ax.bar(off, vals, width, label=_short(m),
               color=MOC if _is_moc(m) else FLAT,
               edgecolor="white", linewidth=0.4,
               hatch="//" if m == "bm25_rag" else None)
    ax.set_xticks(list(x))
    ax.set_xticklabels([c.capitalize() for c in cats])
    ax.set_ylabel("Recall@8 (%)")
    ax.set_title("Recall@8 by query type")
    ax.set_ylim(0, 105)
    # Legend below the axes so it never competes with the bars.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5,
              frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "recall_by_query_type")


def fig_adversarial_recall_drop(var):
    cats = var["categories"]
    methods = var["order"]
    # Positive = how many points recall falls from keyword to adversarial.
    drops = [(var["results"][m][cats[0]]["recall_at_k"]
              - var["results"][m][cats[-1]]["recall_at_k"]) * 100 for m in methods]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh([_short(m) for m in methods], drops, color=_colors(methods),
            edgecolor="white")
    for i, d in enumerate(drops):
        ax.text(d + 0.5, i, f"{d:.0f}", va="center", ha="left", fontsize=8)
    ax.set_xlabel("Recall@8 drop, keyword → adversarial (points)")
    ax.set_title("Recall drop under adversarial shift (lower is better)")
    ax.set_xlim(0, max(drops) * 1.15)
    ax.grid(axis="x", alpha=0.3)
    ax.invert_yaxis()
    _save(fig, "adversarial_recall_drop")


def fig_hard_distractors(var):
    """Hard distractors per method on the adversarial split (lower is better)."""
    cat = var["categories"][-1]
    methods = var["order"]
    vals = [var["results"][m][cat]["hard_distractors"] for m in methods]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([_short(m) for m in methods], vals, color=_colors(methods),
           edgecolor="white")
    ax.set_ylabel("Hard distractors in packs")
    ax.set_title("Hard distractors, adversarial split (lower is better)")
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([_short(m) for m in methods], rotation=30, ha="right",
                       fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "hard_distractors")


def fig_context_efficiency(res):
    methods = res["order"]
    vals = [res["results"][m].get("context_efficiency", 0.0) for m in methods]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([_short(m) for m in methods], vals, color=_colors(methods),
           edgecolor="white")
    ax.set_ylabel("Context efficiency  (Recall@K per 1k tokens)")
    ax.set_title("Context efficiency (mixed test split)")
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels([_short(m) for m in methods], rotation=30, ha="right",
                       fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "context_efficiency")


def fig_routing_accuracy(res):
    methods = [m for m in res["order"]
               if res["results"][m].get("routing_accuracy") is not None]
    vals = [res["results"][m]["routing_accuracy"] * 100 for m in methods]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.bar([_short(m) for m in methods], vals,
           color=[MOC2 if v >= 95 else MOC for v in vals], edgecolor="white")
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
    ax.set_ylabel("Expert routing accuracy (%)")
    ax.set_title("Routing accuracy by MoC-RAG variant")
    ax.set_ylim(0, 108)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "routing_accuracy")


def fig_recall_vs_distractors(var):
    """Pareto: adversarial recall (higher is better) vs hard distractors (lower).

    Conventional axes (x increases left→right): fewer distractors is better, so
    the best region is the upper-left.
    """
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
        ax.annotate(_short(m), (d, r), textcoords="offset points", xytext=(6, 4),
                    fontsize=8, color=MOC2 if moc else "#5f6368")
    ax.set_xlabel("Hard distractors (adversarial) — lower is better")
    ax.set_ylabel("Recall@8 (adversarial) — higher is better")
    ax.set_title("Recall vs harmful context (top-left is best)")
    ax.grid(alpha=0.3)
    _save(fig, "recall_vs_distractors")


def fig_architecture(_=None):
    """MoC-RAG architecture, drawn from matplotlib primitives (not hand-art)."""
    fig, ax = plt.subplots(figsize=(10, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.0)
    ax.axis("off")
    # Pipeline row (kept high so the expert chips below have room).
    row_y = 2.5
    stages = [("Query", 0.7), ("Hybrid\nRouter", 2.4), ("Typed\nExperts", 4.1),
              ("Hybrid\nRetrieval", 5.8), ("Rerank", 7.3),
              ("Budgeted\nPack", 8.7)]
    for label, cx in stages:
        box = FancyBboxPatch((cx - 0.62, row_y), 1.24, 0.8,
                             boxstyle="round,pad=0.04,rounding_size=0.08",
                             linewidth=1.2, edgecolor=MOC2, facecolor="#e8f0fe")
        ax.add_patch(box)
        ax.text(cx, row_y + 0.4, label, ha="center", va="center", fontsize=8.5)
    for (_, x0), (_, x1) in zip(stages, stages[1:]):
        ax.add_patch(FancyArrowPatch((x0 + 0.62, row_y + 0.4),
                                     (x1 - 0.62, row_y + 0.4),
                                     arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.1, color="#5f6368"))
    # Expert chips in two fully-visible rows under the experts stage.
    experts = ["session", "profile", "semantic", "episodic", "document", "policy",
               "decision", "tool"]
    for i, e in enumerate(experts):
        cx = 3.0 + (i % 4) * 0.95
        cy = 1.55 - (i // 4) * 0.5
        ax.add_patch(FancyBboxPatch((cx - 0.42, cy - 0.16), 0.84, 0.32,
                                    boxstyle="round,pad=0.02,rounding_size=0.06",
                                    linewidth=0.6, edgecolor=MOC, facecolor="white",
                                    clip_on=False))
        ax.text(cx, cy, e, ha="center", va="center", fontsize=6.5, clip_on=False)
    # inspect() annotation under the pack stage.
    ax.text(8.7, 1.3, "explainable\ninspect()", ha="center", va="center",
            fontsize=7.5, color=ACCENT)
    ax.add_patch(FancyArrowPatch((8.7, row_y - 0.02), (8.7, 1.62),
                                 arrowstyle="-|>", mutation_scale=10,
                                 color=ACCENT, linewidth=1.0))
    ax.set_title("MoC-RAG routes typed context experts before retrieval",
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
