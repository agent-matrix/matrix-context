"""MoC-RAG Benchmark CLI: build the dataset, run methods, report, push.

    python -m benchmarks.moc_rag_benchmark.run build
    python -m benchmarks.moc_rag_benchmark.run run --split test --embedder hashing
    python -m benchmarks.moc_rag_benchmark.run run --split test --embedder st \
        --algorithms all --generator ollama
    python -m benchmarks.moc_rag_benchmark.run push-results --repo agent-matrix/moc-rag-benchmark
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from . import __benchmark_version__
from .answers import evaluate_answers
from .generate import build as build_dataset
from .metrics import aggregate
from .report import winner, write_reports, write_variant_reports
from .runners import ALGORITHMS, Corpus
from .schema import load_contexts, load_gold, load_queries

PKG = Path(__file__).parent
DATA = PKG / "data"
RESULTS = PKG / "results"

DEFAULT_ALGOS = ["bm25_rag", "dense_rag", "hybrid_rag", "metadata_rag",
                 "reranked_rag", "moc_rag_e1", "moc_rag_e2", "moc_rag_e3",
                 "moc_rag_all"]


def _load_split(data_dir: Path, split: str):
    contexts = load_contexts(data_dir / "contexts.jsonl")
    if split == "all":
        queries = load_queries(data_dir / "queries.jsonl")
        gold = load_gold(data_dir / "gold.jsonl")
    else:
        queries = load_queries(data_dir / "splits" / f"{split}.jsonl")
        gold = load_gold(data_dir / "splits" / f"{split}_gold.jsonl")
    return contexts, queries, gold


def cmd_build(args) -> int:
    from .hf_card import write_card

    counts = build_dataset(DATA, seed=args.seed, min_contexts=args.min_contexts,
                           min_queries=args.min_queries)
    DATA.joinpath("dataset_infos.json").write_text(json.dumps(
        {"benchmark_version": __benchmark_version__, "counts": counts}, indent=2))
    write_card(DATA / "README.md", counts)  # Hugging Face dataset card
    print(f"built dataset at {DATA}")
    for k, v in counts.items():
        print(f"  {k:14s} {v}")
    return 0


def _gold_index(queries, gold_rows):
    q_by_id = {q.query_id: q for q in queries}
    gold_by_qid: Dict[str, dict] = {}
    for g in gold_rows:
        d = g.__dict__.copy()
        d["query"] = q_by_id[g.query_id].query
        gold_by_qid[g.query_id] = d
    expected_by_qid = {q.query_id: q.expected_experts for q in queries}
    return gold_by_qid, expected_by_qid


def _eval_algos(corpus: Corpus, queries, gold_rows, algos, k, budget,
                generator, groundedness) -> Dict[str, dict]:
    gold_by_qid, expected_by_qid = _gold_index(queries, gold_rows)
    out: Dict[str, dict] = {}
    for name in algos:
        runner = ALGORITHMS[name](corpus, budget=budget)
        run_results = [runner.run(q) for q in queries]
        metrics = aggregate(run_results, gold_by_qid, expected_by_qid, k=k)
        if generator is not None or groundedness:
            metrics.update(evaluate_answers(run_results, corpus, gold_by_qid, generator))
        out[name] = metrics
    return out


def _ensure_dataset(seed: int) -> None:
    if not (DATA / "contexts.jsonl").exists():
        print("dataset not found — building it first")
        build_dataset(DATA, seed=seed)


def cmd_run(args) -> int:
    from experiments.backends.embedders import get_embedder
    from experiments.backends.generators import get_generator

    _ensure_dataset(args.seed)
    contexts, queries, gold_rows = _load_split(DATA, args.split)
    corpus = Corpus(contexts, get_embedder(args.embedder))
    algos = DEFAULT_ALGOS if args.algorithms == "all" else args.algorithms.split(",")

    results = _eval_algos(corpus, queries, gold_rows, algos, args.k, args.budget,
                          get_generator(args.generator), args.groundedness)
    for name in algos:
        m = results[name]
        print(f"  {name:14s} recall@{args.k}={m['recall_at_k']:.0%} "
              f"hard_distr={m['hard_distractors']} tokens={m['tokens']} "
              f"route={m['routing_accuracy']}")

    report = {
        "config": {"embedder": args.embedder, "generator": args.generator,
                   "split": args.split, "k": args.k, "budget": args.budget,
                   "queries": len(queries), "contexts": len(contexts),
                   "benchmark_version": __benchmark_version__},
        "order": algos, "results": results, "winner": winner(results),
    }
    out = Path(args.out) if args.out else RESULTS
    write_reports(report, out)
    print(f"\nWinner: {report['winner']}  (reports -> {out})")
    return 0


def cmd_compare(args) -> int:
    """Run every method across the parallel keyword/paraphrased/adversarial test
    splits and report robustness by query type."""
    from experiments.backends.embedders import get_embedder
    from experiments.backends.generators import get_generator
    from .variants import CATEGORIES

    _ensure_dataset(args.seed)
    contexts = load_contexts(DATA / "contexts.jsonl")
    corpus = Corpus(contexts, get_embedder(args.embedder))
    generator = get_generator(args.generator)
    algos = DEFAULT_ALGOS if args.algorithms == "all" else args.algorithms.split(",")

    results: Dict[str, Dict[str, dict]] = {name: {} for name in algos}
    for cat in CATEGORIES:
        split_name = f"test_{cat}"
        queries = load_queries(DATA / "splits" / f"{split_name}.jsonl")
        gold_rows = load_gold(DATA / "splits" / f"{split_name}_gold.jsonl")
        per_algo = _eval_algos(corpus, queries, gold_rows, algos, args.k, args.budget,
                               generator, args.groundedness)
        for name in algos:
            results[name][cat] = per_algo[name]
        print(f"[{cat:11s}] " + "  ".join(
            f"{n.split('_')[0]}:{results[n][cat]['recall_at_k']:.0%}" for n in algos))

    report = {
        "config": {"embedder": args.embedder, "generator": args.generator,
                   "k": args.k, "budget": args.budget,
                   "benchmark_version": __benchmark_version__},
        "categories": CATEGORIES, "order": algos, "results": results,
    }
    out = Path(args.out) if args.out else (RESULTS / args.embedder)
    write_variant_reports(report, out)
    print(f"\nrobustness report -> {out}/variants_summary.md")
    return 0


def cmd_push(args) -> int:
    from .push_to_hub import push_dataset, push_results
    if args.dataset:
        push_dataset(args.repo, DATA, private=args.private)
    if args.results:
        push_results(args.repo, args.results)
    if not (args.dataset or args.results):
        print("nothing to push: pass --dataset and/or --results <file>")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="moc-rag-benchmark")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="generate the dataset")
    b.add_argument("--seed", type=int, default=13)
    b.add_argument("--min-contexts", type=int, default=1000)
    b.add_argument("--min-queries", type=int, default=300)
    b.set_defaults(func=cmd_build)

    r = sub.add_parser("run", help="run methods on one split and report")
    r.add_argument("--split", default="test",
                   help="train | validation | test | all | test_keyword | "
                        "test_paraphrased | test_adversarial")
    r.add_argument("--embedder", default="hashing", help="hashing | st | ollama")
    r.add_argument("--algorithms", default="all", help="'all' or comma-separated names")
    r.add_argument("--generator", default="none", help="none | ollama (answer quality)")
    r.add_argument("--groundedness", action="store_true",
                   help="compute offline groundedness/citation proxies without a generator")
    r.add_argument("--budget", type=int, default=200)
    r.add_argument("--k", type=int, default=8)
    r.add_argument("--seed", type=int, default=13)
    r.add_argument("--out", default="")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("compare", help="robustness by query type "
                       "(keyword vs paraphrased vs adversarial)")
    c.add_argument("--embedder", default="hashing", help="hashing | st | ollama")
    c.add_argument("--algorithms", default="all", help="'all' or comma-separated names")
    c.add_argument("--generator", default="none")
    c.add_argument("--groundedness", action="store_true")
    c.add_argument("--budget", type=int, default=200)
    c.add_argument("--k", type=int, default=8)
    c.add_argument("--seed", type=int, default=13)
    c.add_argument("--out", default="")
    c.set_defaults(func=cmd_compare)

    pu = sub.add_parser("push-results", help="push dataset and/or results to HF Hub")
    pu.add_argument("--repo", required=True)
    pu.add_argument("--dataset", action="store_true", help="push the dataset files")
    pu.add_argument("--results", default="", help="path to a results json/dir to push")
    pu.add_argument("--private", action="store_true")
    pu.set_defaults(func=cmd_push)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
