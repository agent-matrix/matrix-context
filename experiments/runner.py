"""Algorithm bake-off runner.

Runs every algorithm over the dataset with one embedder/store held constant,
scores retrieval (and optionally answer quality via a small LLM), and writes a
summary. Offline default:  python -m experiments.runner
Real local run:  python -m experiments.runner --embedder ollama --store chroma --generator ollama
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

from .algorithms import ALGORITHMS
from .backends.embedders import get_embedder
from .backends.generators import get_generator
from .datasets.loader import load
from . import metrics

RESULTS = Path(__file__).parent / "results"


def run(embedder_name: str, store_name: str, generator_name: str,
        budget: int) -> Dict:
    embedder = get_embedder(embedder_name)
    generator = get_generator(generator_name)
    items, queries = load()
    content_to_id = {it.content: it.id for it in items}

    summary: List[Dict] = []
    for algo_cls in ALGORITHMS.values():
        algo = algo_cls(embedder, store_name=store_name)
        algo.prepare([_clone(it) for it in items])
        agg = {"recall": 0.0, "distract": 0, "tokens": 0, "latency_ms": 0.0,
               "correct": 0, "answered": 0}
        for q in queries:
            gold = set(q["gold_ids"])
            t0 = time.perf_counter()
            ctx = algo.build_context(q["text"], budget)
            agg["latency_ms"] += (time.perf_counter() - t0) * 1000
            pack_ids = {content_to_id.get(c, c) for c in ctx.contents}
            agg["recall"] += metrics.recall(pack_ids, gold)
            agg["distract"] += metrics.distractors(len(ctx.contents), pack_ids, gold)
            agg["tokens"] += ctx.tokens
            if generator is not None:
                ans = generator.answer(q["text"], ctx.text())
                ok = (generator.judge(q["text"], q["gold_answer"], ans)
                      if hasattr(generator, "judge") else
                      metrics.keyword_correct(ans, q["gold_answer"]))
                agg["correct"] += int(ok); agg["answered"] += 1
        n = len(queries)
        summary.append({
            "algorithm": algo.name,
            "recall": round(agg["recall"] / n, 3),
            "distractors": agg["distract"],
            "tokens": agg["tokens"],
            "latency_ms": round(agg["latency_ms"] / n, 2),
            "accuracy": (round(agg["correct"] / agg["answered"], 3)
                         if agg["answered"] else None),
        })
    return {"config": {"embedder": embedder_name, "store": store_name,
                       "generator": generator_name, "budget": budget},
            "results": summary, "winner": _winner(summary)}


def _clone(it):
    from matrix_context.schema.item import ContextItem
    return ContextItem(id=it.id, content=it.content, expert=it.expert,
                       importance=it.importance)


def _winner(summary: List[Dict]) -> str:
    # rank: highest accuracy (if measured) else recall, then fewest distractors, then fewest tokens
    def key(r):
        primary = r["accuracy"] if r["accuracy"] is not None else r["recall"]
        return (-primary, r["distractors"], r["tokens"])
    return sorted(summary, key=key)[0]["algorithm"]


def render(report: Dict) -> str:
    c = report["config"]
    out = [f"# Bake-off — embedder={c['embedder']} store={c['store']} "
           f"generator={c['generator']} budget={c['budget']}", "",
           "| algorithm | recall | distractors | tokens | latency_ms | accuracy |",
           "|---|---|---|---|---|---|"]
    for r in report["results"]:
        acc = "-" if r["accuracy"] is None else f"{r['accuracy']:.0%}"
        out.append(f"| {r['algorithm']} | {r['recall']:.0%} | {r['distractors']} | "
                   f"{r['tokens']} | {r['latency_ms']} | {acc} |")
    out += ["", f"**Winner:** `{report['winner']}`",
            "", "_accuracy is shown only when a generator is configured "
            "(offline runs leave it blank and rank on recall/distractors/tokens)._"]
    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--embedder", default="hashing")
    p.add_argument("--store", default="memory")
    p.add_argument("--generator", default="none")
    p.add_argument("--budget", type=int, default=90)
    args = p.parse_args(argv)

    report = run(args.embedder, args.store, args.generator, args.budget)
    md = render(report)
    print(md)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "summary.md").write_text(md)
    (RESULTS / "results.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
