"""Render benchmark results as JSON and a publication-style Markdown table."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

# Column order for the Markdown table (publication layout).
_COLS = [
    ("recall_at_k", "Recall@K", "{:.0%}"),
    ("precision_at_k", "Prec@K", "{:.0%}"),
    ("mrr", "MRR", "{:.3f}"),
    ("ndcg_at_k", "nDCG@K", "{:.3f}"),
    ("hard_distractors", "HardDistr ↓", "{}"),
    ("distractors", "Distr ↓", "{}"),
    ("tokens", "Tokens ↓", "{}"),
    ("useful_context_ratio", "UsefulRatio ↑", "{:.0%}"),
    ("context_efficiency", "CtxEff ↑", "{:.3f}"),
    ("routing_accuracy", "RouteAcc", "{:.0%}"),
    ("latency_ms", "Lat(ms)", "{:.2f}"),
    ("answer_correctness", "AnsAcc", "{:.0%}"),
    ("groundedness", "Ground", "{:.0%}"),
]


def winner(results: Dict[str, dict]) -> str:
    """Rank: answer correctness if measured else recall, then fewest hard
    distractors, then fewest tokens."""
    def key(name):
        m = results[name]
        primary = m.get("answer_correctness")
        if primary is None:
            primary = m.get("recall_at_k", 0.0)
        return (-primary, m.get("hard_distractors", 0), m.get("tokens", 0))
    return sorted(results, key=key)[0]


def _fmt(val, spec) -> str:
    if val is None:
        return "-"
    try:
        return spec.format(val)
    except (ValueError, TypeError):
        return str(val)


def render_markdown(report: dict) -> str:
    cfg = report["config"]
    results: Dict[str, dict] = report["results"]
    cols = [c for c in _COLS if any(c[0] in m for m in results.values())]
    head = "| Method | " + " | ".join(label for _, label, _ in cols) + " |"
    sep = "|" + "---|" * (len(cols) + 1)
    lines = [
        f"# MoC-RAG Benchmark — {cfg.get('split', 'test')} split",
        "",
        f"embedder=`{cfg['embedder']}` · K={cfg['k']} · budget={cfg['budget']} tokens "
        f"· queries={cfg['queries']} · contexts={cfg['contexts']}",
        "",
        head, sep,
    ]
    for name in report["order"]:
        m = results[name]
        row = [name] + [_fmt(m.get(key), spec) for key, _, spec in cols]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", f"**Winner:** `{report['winner']}`", "",
              "_Ranked by answer correctness when measured, else Recall@K, then "
              "fewest hard distractors, then fewest tokens. ↓ lower is better, "
              "↑ higher is better._"]
    return "\n".join(lines)


def write_reports(report: dict, out_dir: Path,
                  per_algo: Optional[List[str]] = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.md").write_text(render_markdown(report))
    (out_dir / "results.json").write_text(json.dumps(report, indent=2))
    # Per-algorithm artifact (the format the HF push expects).
    for name in (per_algo or report["order"]):
        m = report["results"][name]
        artifact = {"algorithm": name, "config": report["config"], "metrics": m}
        (out_dir / f"{name}.json").write_text(json.dumps(artifact, indent=2))


def render_variant_comparison(report: dict) -> str:
    """Robustness table: Recall@K and hard distractors per query category, so
    lexical degradation (keyword -> paraphrased -> adversarial) is visible."""
    cfg = report["config"]
    cats = report["categories"]
    results = report["results"]  # {method: {category: metrics}}
    head = ("| Method | " + " | ".join(f"R@{cfg['k']} {c}" for c in cats) + " | "
            + " | ".join(f"HardDistr {c}" for c in cats) + " | RouteAcc |")
    sep = "|" + "---|" * (1 + 2 * len(cats) + 1)
    lines = [
        "# MoC-RAG Benchmark — robustness by query type",
        "",
        f"embedder=`{cfg['embedder']}` · K={cfg['k']} · budget={cfg['budget']} tokens "
        f"· parallel test topics phrased as {', '.join(cats)}",
        "",
        "Recall@K should hold across columns; a method that **drops** from "
        "`keyword` to `adversarial` is brittle to lexical noise.",
        "", head, sep,
    ]
    for name in report["order"]:
        rec = [_fmt(results[name][c].get("recall_at_k"), "{:.0%}") for c in cats]
        hd = [_fmt(results[name][c].get("hard_distractors"), "{}") for c in cats]
        ra = results[name][cats[-1]].get("routing_accuracy")
        lines.append("| " + " | ".join([name] + rec + hd + [_fmt(ra, "{:.0%}")]) + " |")

    # Degradation summary: recall drop keyword -> adversarial.
    lines += ["", "## Recall drop (keyword → adversarial)", "",
              "| Method | Δ Recall@K |", "|---|---|"]
    for name in report["order"]:
        first = results[name][cats[0]].get("recall_at_k", 0.0)
        last = results[name][cats[-1]].get("recall_at_k", 0.0)
        lines.append(f"| {name} | {last - first:+.0%} |")
    return "\n".join(lines)


def write_variant_reports(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "variants_summary.md").write_text(render_variant_comparison(report))
    (out_dir / "variants.json").write_text(json.dumps(report, indent=2))
