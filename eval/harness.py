"""Feasibility / impact harness.

Loads the typed memory set + queries, then compares three systems on the same
budget: STUB (offline hashing gate), CMPT (competent gate = real-embedder
regime), FLAT (classic RAG). Run:  python -m eval.harness
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Set

from matrix_context import ContextManager, HashingEmbedder
from matrix_context.context.assembler import assemble_pack
from matrix_context.retrieval.fusion import hybrid_retrieve

from .baselines import flat_rag
from . import metrics
from .report import render

DATA_DIR = Path(__file__).parent / "datasets"
BUDGET = 90


def _load(name: str) -> List[dict]:
    rows = []
    for line in (DATA_DIR / name).read_text().splitlines():
        line = line.strip()
        if line:
            obj = json.loads(line)
            if "_comment" not in obj:
                rows.append(obj)
    return rows


def run() -> List[dict]:
    emb = HashingEmbedder()
    ctx = ContextManager.create("eval", path=":memory:", embedder=emb)
    data = _load("synthetic_typed.jsonl")
    for r in data:
        ctx.remember(r["content"], expert=r["expert"], importance=r["importance"])
    queries = _load("queries.jsonl")
    gold: Dict[str, Set[str]] = {
        q["id"]: {r["content"] for r in data if r.get("gold_for") == q["id"]}
        for q in queries}

    all_items = ctx.store.all_items()
    results = []
    for q in queries:
        qid, qtext, want = q["id"], q["text"], q["expert"]
        g = gold[qid]
        # STUB: full engine with the offline hashing gate
        decision, scores, by_id = ctx._route_and_score(qtext, "/", top_experts=2)
        stub = assemble_pack(scores, by_id, decision.selected, decision.reason, max_tokens=BUDGET)
        stub_c = [p.item.content for p in stub.items]
        # CMPT: competent gate -> route straight to the correct expert
        cc = ctx.store.candidates([want], "/")
        cbid = {it.id: it for it in cc}
        cs = hybrid_retrieve(qtext, emb.encode(qtext), cc) if cc else {}
        cmpt = assemble_pack(cs, cbid, [want], "competent-gate", max_tokens=BUDGET)
        cmpt_c = [p.item.content for p in cmpt.items]
        # FLAT: classic RAG
        flat_c, flat_tok = flat_rag(qtext, emb, all_items, BUDGET)
        results.append({
            "qid": qid, "gold": len(g),
            "stub_recall": metrics.gold_recall(stub_c, g),
            "stub_dist": metrics.distractor_count(stub_c, g),
            "route_hit": metrics.routing_hit(decision.selected, want),
            "cmpt_recall": metrics.gold_recall(cmpt_c, g),
            "cmpt_dist": metrics.distractor_count(cmpt_c, g),
            "cmpt_tok": cmpt.tokens,
            "flat_recall": metrics.gold_recall(flat_c, g),
            "flat_dist": metrics.distractor_count(flat_c, g),
            "flat_tok": flat_tok,
        })
    return results


if __name__ == "__main__":
    print(render(run()))
