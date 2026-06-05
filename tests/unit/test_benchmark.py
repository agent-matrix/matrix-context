"""MoC-RAG Benchmark: generation, metrics, runners, reporting contracts.

Runs fully offline with the hashing embedder (CI guard). Asserts the dataset
meets the published targets and integrity, that every runner produces
well-formed results, that metrics aggregate the full contract, and that the
hybrid router actually routes (routing accuracy is reported for MoC variants).
"""
from benchmarks.moc_rag_benchmark.generate import generate, split
from benchmarks.moc_rag_benchmark.metrics import (aggregate, ndcg_at_k,
                                                  precision_at_k, recall_at_k,
                                                  reciprocal_rank)
from benchmarks.moc_rag_benchmark.report import (render_markdown,
                                                 render_variant_comparison, winner)
from benchmarks.moc_rag_benchmark.runners import ALGORITHMS, Corpus
from benchmarks.moc_rag_benchmark.hf_card import dataset_card
from benchmarks.moc_rag_benchmark.variants import (CATEGORIES, VARIANT_CATEGORY,
                                                   make_variants)
from matrix_context.embedding.hashing import HashingEmbedder


# --------------------------------------------------------------- dataset
def test_generate_meets_targets_and_integrity():
    contexts, queries, gold = generate()
    assert len(contexts) >= 1000 and len(queries) >= 300
    assert len({c.expert for c in contexts}) == 8
    assert len({c.type for c in contexts}) >= 10
    assert len({q.domain for q in queries}) == 6
    assert len({c.negative_kind for c in contexts if c.negative_kind}) == 5

    ids = {c.context_id for c in contexts}
    for g in gold:
        assert g.gold_context_ids and set(g.gold_context_ids) <= ids
        assert set(g.distractor_context_ids) <= ids
        assert g.gold_answer


def test_committed_dataset_is_frozen_and_reproducible():
    """The committed dataset must equal the deterministic seed-13 generation.

    This freezes the published benchmark: the dataset/results are the source of
    truth for the paper and the HF dataset. If generation logic ever changes,
    this fails loudly so the data is re-frozen intentionally (and the numbers
    re-published) rather than drifting silently. CI never regenerates it.
    """
    import json
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[2] / "benchmarks" / "moc_rag_benchmark" / "data"
    if not (data_dir / "contexts.jsonl").exists():
        import pytest
        pytest.skip("committed dataset not present in this checkout")

    contexts, queries, _ = generate()
    committed_ctx = [json.loads(x) for x in (data_dir / "contexts.jsonl").read_text().splitlines()]
    committed_q = [json.loads(x) for x in (data_dir / "queries.jsonl").read_text().splitlines()]

    assert [c.context_id for c in contexts] == [c["context_id"] for c in committed_ctx]
    assert [c.content for c in contexts] == [c["content"] for c in committed_ctx]
    assert [q.query for q in queries] == [q["query"] for q in committed_q]


def test_splits_are_disjoint_and_cover():
    _, queries, _ = generate()
    sp = split(queries)
    train, val, test = set(sp["train"]), set(sp["validation"]), set(sp["test"])
    assert not (train & val) and not (train & test) and not (val & test)
    assert train | val | test == {q.query_id for q in queries}


# --------------------------------------------------------------- variants
def test_five_variants_per_topic_with_stable_gold():
    contexts, queries, gold = generate()
    # exactly five variant kinds, one query each per topic
    assert {q.variant for q in queries} == {
        "direct", "paraphrased", "underspecified", "cross_expert", "adversarial"}
    gold_by_qid = {g.query_id: tuple(g.gold_context_ids) for g in gold}
    by_topic = {}
    for q in queries:
        by_topic.setdefault(q.topic, []).append(q.query_id)
    # every variant of a topic points at the SAME gold ids
    for topic, qids in by_topic.items():
        assert len({gold_by_qid[i] for i in qids}) == 1, topic


def test_variant_test_splits_are_parallel():
    _, queries, _ = generate()
    sp = split(queries)
    topic_of = {q.query_id: q.topic for q in queries}
    cats = {c: {topic_of[i] for i in sp[f"test_{c}"]} for c in CATEGORIES}
    # the three variant test splits cover exactly the same topics (parallel)
    assert cats["keyword"] == cats["paraphrased"] == cats["adversarial"]
    # and those are the test-split topics
    assert cats["keyword"] == {topic_of[i] for i in sp["test"]}


def test_adversarial_query_embeds_misleading_term():
    """Adversarial variants reuse the topic's `wrong` value — the same value the
    contradictory hard negative uses — so flat retrieval is genuinely tempted."""
    contexts, queries, _ = generate()
    topic_wrong = {}
    # recover each topic's `wrong` via its contradictory negative text
    from benchmarks.moc_rag_benchmark.generate import _topics
    for t in _topics():
        topic_wrong[t.topic_id] = t.wrong
    adv = [q for q in queries if q.variant == "adversarial"]
    hits = sum(1 for q in adv if topic_wrong[q.topic].split()[0].lower() in q.query.lower())
    assert hits / len(adv) >= 0.8     # most adversarial queries carry the misleading term
    assert set(VARIANT_CATEGORY) == {"direct", "paraphrased", "underspecified",
                                     "cross_expert", "adversarial"}


def test_variant_comparison_report_renders():
    cats = CATEGORIES
    results = {
        "bm25_rag": {c: {"recall_at_k": r, "hard_distractors": 50, "routing_accuracy": None}
                     for c, r in zip(cats, [1.0, 0.8, 0.6])},
        "moc_rag_e2": {c: {"recall_at_k": r, "hard_distractors": 20, "routing_accuracy": 0.95}
                       for c, r in zip(cats, [1.0, 0.85, 0.8])},
    }
    report = {"config": {"embedder": "hashing", "k": 8, "budget": 200},
              "categories": cats, "order": list(results), "results": results}
    md = render_variant_comparison(report)
    assert "robustness by query type" in md
    assert "bm25_rag" in md and "Recall drop" in md
    assert "-40%" in md  # bm25 drops 1.0 -> 0.6 on adversarial


def test_make_variants_covers_all_kinds():
    contexts, _, _ = generate()
    from benchmarks.moc_rag_benchmark.generate import _topics
    for t in _topics()[:5]:
        kinds = {v for v, _t, _d in make_variants(t)}
        assert kinds == {"direct", "paraphrased", "underspecified",
                         "cross_expert", "adversarial"}


# --------------------------------------------------------------- metrics
def test_ranking_metrics():
    ranked = ["a", "b", "c", "d"]
    rel = {"b", "d"}
    assert recall_at_k(ranked, rel, 4) == 1.0
    assert recall_at_k(ranked, rel, 1) == 0.0
    assert precision_at_k(ranked, rel, 2) == 0.5
    assert reciprocal_rank(ranked, rel) == 0.5
    assert 0.0 < ndcg_at_k(ranked, rel, 4) <= 1.0
    # empty gold -> recall defined as 1.0 (nothing to miss)
    assert recall_at_k(ranked, set(), 4) == 1.0


# --------------------------------------------------------------- runners
def _small():
    contexts, queries, gold = generate()
    corpus = Corpus(contexts, HashingEmbedder())
    queries = queries[:12]
    gold_by_qid = {g.query_id: g.__dict__ for g in gold}
    expected = {q.query_id: q.expected_experts for q in queries}
    return corpus, queries, gold_by_qid, expected


def test_every_runner_produces_well_formed_results():
    corpus, queries, gold_by_qid, expected = _small()
    for name, factory in ALGORITHMS.items():
        runner = factory(corpus, budget=200)
        results = [runner.run(q) for q in queries]
        assert all(r.ranked_ids for r in results)
        for r in results:
            # kept ids are a prefix-subset of the ranked candidates
            assert set(r.kept_ids) <= set(r.ranked_ids)
            assert r.tokens <= 200
        m = aggregate(results, gold_by_qid, expected, k=8)
        assert set(m) >= {"recall_at_k", "precision_at_k", "mrr", "ndcg_at_k",
                          "hard_distractors", "tokens", "useful_context_ratio",
                          "context_efficiency", "routing_accuracy"}
        assert 0.0 <= m["recall_at_k"] <= 1.0


def test_moc_is_routed_others_are_not():
    corpus, queries, gold_by_qid, expected = _small()
    flat = aggregate([ALGORITHMS["bm25_rag"](corpus).run(q) for q in queries],
                     gold_by_qid, expected)
    moc = aggregate([ALGORITHMS["moc_rag_e3"](corpus).run(q) for q in queries],
                    gold_by_qid, expected)
    assert flat["routing_accuracy"] is None       # flat RAG does not route
    assert moc["routing_accuracy"] is not None     # MoC reports routing accuracy
    assert moc["routing_accuracy"] >= 0.5          # hybrid priors route sensibly


def test_moc_cuts_hard_distractors_vs_bm25():
    """On the synthetic set the hybrid router should pack fewer labeled hard
    negatives than flat BM25 at comparable recall — the benchmark's thesis."""
    corpus, queries, gold_by_qid, expected = _small()
    bm = aggregate([ALGORITHMS["bm25_rag"](corpus).run(q) for q in queries],
                   gold_by_qid, expected)
    moc = aggregate([ALGORITHMS["moc_rag_e2"](corpus).run(q) for q in queries],
                    gold_by_qid, expected)
    assert moc["hard_distractors"] <= bm["hard_distractors"]


# --------------------------------------------------------------- reporting
def test_report_and_card_render():
    results = {"bm25_rag": {"recall_at_k": 0.9, "hard_distractors": 60, "tokens": 100},
               "moc_rag_e2": {"recall_at_k": 0.9, "hard_distractors": 30, "tokens": 90}}
    assert winner(results) == "moc_rag_e2"   # same recall, fewer hard distractors
    report = {"config": {"embedder": "hashing", "k": 8, "budget": 200,
                         "queries": 2, "contexts": 10, "split": "test"},
              "order": list(results), "results": results, "winner": "moc_rag_e2"}
    md = render_markdown(report)
    assert "moc_rag_e2" in md and "Recall@K" in md and "Winner" in md

    card = dataset_card({"contexts": 1000, "queries": 300, "experts": 8})
    assert "license: apache-2.0" in card and "Hard negatives" in card
