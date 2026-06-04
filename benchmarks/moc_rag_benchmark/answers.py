"""Optional answer-quality evaluation.

Given each method's assembled pack, optionally generate an answer with a small
local LLM and score it. ``groundedness`` is a cheap offline proxy (is the gold
answer supported by the packed context?) computed even without a generator;
``answer_correctness`` requires a generator (reuses the experiments Ollama
backend, with a keyword-overlap judge as the offline fallback).
"""
from __future__ import annotations

from typing import Dict, List

from experiments.metrics import keyword_correct

from .metrics import RunResult
from .runners import Corpus


def _content_words(text: str) -> List[str]:
    return [w for w in text.lower().split() if len(w) > 3]


def _supported(gold_answer: str, pack_text: str) -> bool:
    words = _content_words(gold_answer)
    if not words:
        return False
    hit = sum(1 for w in words if w in pack_text.lower())
    return hit / len(words) >= 0.5


def evaluate_answers(results: List[RunResult], corpus: Corpus,
                     gold_by_qid: Dict[str, dict],
                     generator=None) -> Dict[str, float]:
    """Return answer-quality metrics aggregated over the queries."""
    n = len(results) or 1
    grounded = 0
    correct = 0
    answered = 0
    cited = 0
    for r in results:
        g = gold_by_qid[r.query_id]
        pack_text = "\n".join(corpus.by_id[i].content for i in r.kept_ids)
        gold_answer = g.get("gold_answer", "")
        if _supported(gold_answer, pack_text):
            grounded += 1
        # Citation support: a gold citation actually made it into the pack.
        if set(g.get("gold_citations", [])) & set(r.kept_ids):
            cited += 1
        if generator is not None:
            ans = generator.answer(g.get("query", ""), pack_text) \
                if hasattr(generator, "answer") else ""
            ok = (generator.judge(g.get("query", ""), gold_answer, ans)
                  if hasattr(generator, "judge") else keyword_correct(ans, gold_answer))
            correct += int(ok)
            answered += 1
    out = {
        "groundedness": round(grounded / n, 4),
        "citation_support": round(cited / n, 4),
    }
    if answered:
        out["answer_correctness"] = round(correct / answered, 4)
    return out
