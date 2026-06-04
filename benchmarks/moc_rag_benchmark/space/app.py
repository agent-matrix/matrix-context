"""MoC-RAG Benchmark leaderboard — Gradio Space.

Self-contained: reads the bundled result artifacts in ``results/<embedder>/`` and
renders (1) the single-split leaderboard and (2) the robustness-by-query-type
table that is the headline of the benchmark. No dataset access or token needed.
"""
import json
from pathlib import Path

import gradio as gr
import pandas as pd

RESULTS = Path(__file__).parent / "results"
EMBEDDERS = [p.name for p in sorted(RESULTS.iterdir()) if p.is_dir()]

LEADERBOARD_COLS = [
    ("recall_at_k", "Recall@K"), ("precision_at_k", "Prec@K"), ("mrr", "MRR"),
    ("ndcg_at_k", "nDCG@K"), ("hard_distractors", "HardDistr↓"),
    ("tokens", "Tokens↓"), ("useful_context_ratio", "UsefulRatio↑"),
    ("context_efficiency", "CtxEff↑"), ("routing_accuracy", "RouteAcc"),
    ("groundedness", "Ground"),
]


def _pct(v):
    return "-" if v is None else (f"{v:.0%}" if isinstance(v, float) and v <= 1 else v)


def leaderboard(embedder: str) -> pd.DataFrame:
    rep = json.loads((RESULTS / embedder / "results.json").read_text())
    rows = []
    for name in rep["order"]:
        m = rep["results"][name]
        row = {"Method": name}
        for key, label in LEADERBOARD_COLS:
            v = m.get(key)
            row[label] = _pct(v) if key in (
                "recall_at_k", "precision_at_k", "useful_context_ratio",
                "routing_accuracy", "groundedness") else (v if v is not None else "-")
        rows.append(row)
    return pd.DataFrame(rows)


def robustness(embedder: str) -> pd.DataFrame:
    rep = json.loads((RESULTS / embedder / "variants.json").read_text())
    cats = rep["categories"]
    rows = []
    for name in rep["order"]:
        r = rep["results"][name]
        row = {"Method": name}
        for c in cats:
            row[f"R@K {c}"] = _pct(r[c].get("recall_at_k"))
        for c in cats:
            row[f"HardDistr {c}"] = r[c].get("hard_distractors")
        first = r[cats[0]].get("recall_at_k", 0.0)
        last = r[cats[-1]].get("recall_at_k", 0.0)
        row["Δ kw→adv"] = f"{last - first:+.0%}"
        rows.append(row)
    return pd.DataFrame(rows)


INTRO = """
# 🧭 MoC-RAG Benchmark Leaderboard

Does **routed, typed context** (Mixture-of-Contexts RAG) beat **flat RAG** for
agentic memory? This leaderboard reports retrieval, context-efficiency, routing,
and robustness metrics for BM25 / dense / hybrid / metadata-filtered / reranked
RAG and MoC-RAG (`top_experts ∈ {1,2,3,all}`).

**Headline (sentence-transformers):** BM25 collapses on adversarial queries
(−36% vs keyword), while MoC-RAG holds and **overtakes BM25 by ~+15 points on the
adversarial split**, carrying roughly half the hard distractors of dense RAG at
95–100% routing accuracy.

Dataset: [`ruslanmv/moc-rag-benchmark`](https://huggingface.co/datasets/ruslanmv/moc-rag-benchmark).
"""


def build():
    with gr.Blocks(title="MoC-RAG Benchmark Leaderboard") as demo:
        gr.Markdown(INTRO)
        emb = gr.Dropdown(EMBEDDERS, value=("st" if "st" in EMBEDDERS else EMBEDDERS[0]),
                          label="Embedder")
        gr.Markdown("## Robustness by query type (the key result)")
        rob = gr.Dataframe(value=robustness("st" if "st" in EMBEDDERS else EMBEDDERS[0]),
                           interactive=False)
        gr.Markdown("## Single-split leaderboard")
        lead = gr.Dataframe(value=leaderboard("st" if "st" in EMBEDDERS else EMBEDDERS[0]),
                            interactive=False)
        emb.change(robustness, emb, rob)
        emb.change(leaderboard, emb, lead)
    return demo


if __name__ == "__main__":
    build().launch()
