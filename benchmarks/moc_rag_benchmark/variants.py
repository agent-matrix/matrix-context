"""Paraphrased / adversarial query variant generator.

For each gold topic this produces five query phrasings that hold the gold label
constant while varying lexical overlap and intent:

    direct          high keyword overlap with the gold (lexical-friendly)
    paraphrased     reworded, semantic match, low keyword overlap
    underspecified  vague / missing specifics
    cross_expert    phrased from a neighbouring angle (tests routing)
    adversarial     embeds a MISLEADING term (the topic's ``wrong`` value) that
                    lexically matches the contradictory hard negative

The adversarial phrasings deliberately reuse ``topic.wrong`` — the same value
that appears in the ``contradictory_memory`` negative — so a flat lexical/dense
retriever is tempted toward the wrong item, while a good router still selects the
correct typed experts and retrieves the real decision.

Variants are grouped into evaluation categories:
    keyword      = {direct}
    paraphrased  = {paraphrased, underspecified}
    adversarial  = {cross_expert, adversarial}
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# variant -> category used to build the test_keyword/paraphrased/adversarial splits
VARIANT_CATEGORY: Dict[str, str] = {
    "direct": "keyword",
    "paraphrased": "paraphrased",
    "underspecified": "paraphrased",
    "cross_expert": "adversarial",
    "adversarial": "adversarial",
}
CATEGORIES = ["keyword", "paraphrased", "adversarial"]


def _entity(scope: str) -> str:
    return scope.split(":", 1)[-1] if ":" in scope else scope


# Per-template (topic.key) phrasings. Each returns
# {variant: (text, difficulty)} given the topic's fields.
def _phrasings(key: str, e: str, kw: str, ans: str, wrong: str) -> Dict[str, Tuple[str, str]]:
    P: Dict[str, Dict[str, Tuple[str, str]]] = {
        "backend": {
            "direct": (f"What is the default storage backend in {e}?", "easy"),
            "paraphrased": (f"For {e}, what does the team rely on for local persistence out of the box?", "medium"),
            "underspecified": (f"What does {e} keep its data in?", "hard"),
            "cross_expert": (f"Is there a documented decision about how {e} stores data on disk?", "medium"),
            "adversarial": (f"Should {e} use {wrong} as the required storage backend?", "hard"),
        },
        "interfaces": {
            "direct": (f"What interfaces does {e} expose?", "easy"),
            "paraphrased": (f"How are external AI clients supposed to connect to {e}'s context layer?", "medium"),
            "underspecified": (f"How do you talk to {e}?", "hard"),
            "cross_expert": (f"Which integration surfaces are part of {e}'s architecture?", "medium"),
            "adversarial": (f"Does {e} only provide {wrong}?", "hard"),
        },
        "milvus_defer": {
            "direct": (f"When will {e} add Milvus?", "medium"),
            "paraphrased": (f"Which release of {e} postpones vector-database support?", "medium"),
            "underspecified": (f"What got pushed back in {e}?", "hard"),
            "cross_expert": (f"Is there a roadmap decision about scaling storage in {e}?", "medium"),
            "adversarial": (f"Is Milvus required in {e} {wrong}?", "hard"),
        },
        "pref_local": {
            "direct": (f"What does the {e} prefer for local vs cloud tools?", "easy"),
            "paraphrased": (f"When the {e} picks tooling, which way does it lean?", "medium"),
            "underspecified": (f"What are the {e}'s tool preferences?", "hard"),
            "cross_expert": (f"Any profile note on how the {e} treats hosted services?", "medium"),
            "adversarial": (f"Does the {e} prefer {wrong} managed cloud services?", "hard"),
        },
        "pref_tone": {
            "direct": (f"What tone should the {e} use?", "easy"),
            "paraphrased": (f"How should replies to the {e} come across in style?", "medium"),
            "underspecified": (f"How should the {e} sound?", "hard"),
            "cross_expert": (f"Is the {e}'s communication style recorded anywhere?", "medium"),
            "adversarial": (f"Should the {e} be {wrong}?", "hard"),
        },
        "code_loc": {
            "direct": (f"Where is the {kw} implemented in {e}?", "medium"),
            "paraphrased": (f"Which source file is responsible for {kw} behaviour in {e}?", "medium"),
            "underspecified": (f"Where's the {kw} in {e}?", "hard"),
            "cross_expert": (f"Point me to the module that handles {kw} for {e}.", "medium"),
            "adversarial": (f"Is the {kw} for {e} defined in {wrong}?", "hard"),
        },
        "policy": {
            "direct": (f"Can the agent store {kw} in {e}?", "medium"),
            "paraphrased": (f"How must {e} handle {kw} when persisting memory?", "medium"),
            "underspecified": (f"What about {kw} in {e}?", "hard"),
            "cross_expert": (f"Is there a rule covering {kw} for {e}?", "medium"),
            "adversarial": (f"Is {e} allowed to {wrong} in durable memory?", "hard"),
        },
        "tool_result": {
            "direct": (f"What was the last {kw} result on {e}?", "easy"),
            "paraphrased": (f"How did the most recent {kw} check go for {e}?", "medium"),
            "underspecified": (f"How's {kw} on {e}?", "hard"),
            "cross_expert": (f"Any tool-run record for {kw} on {e}?", "medium"),
            "adversarial": (f"Did the last {kw} run on {e} end up {wrong}?", "hard"),
        },
        "session_episode": {
            "direct": (f"What did we agree last session about {e}?", "medium"),
            "paraphrased": (f"In our recent discussion on {e}, what was the agreed first deliverable?", "medium"),
            "underspecified": (f"What did we say about {e}?", "hard"),
            "cross_expert": (f"Is there a session note on {e} priorities?", "medium"),
            "adversarial": (f"Did we agree to build {wrong} for {e}?", "hard"),
        },
        "doc": {
            "direct": (f"What does the {e} whitepaper say in the {kw} section?", "medium"),
            "paraphrased": (f"According to {e}'s paper, what is the effect of routed typed context on noise?", "medium"),
            "underspecified": (f"What's in the {e} {kw} part?", "hard"),
            "cross_expert": (f"Does {e}'s documentation report a distractor result?", "medium"),
            "adversarial": (f"Does the {e} whitepaper claim routing {wrong}?", "hard"),
        },
    }
    return P[key]


def make_variants(topic) -> List[Tuple[str, str, str]]:
    """Return [(variant, query_text, difficulty), ...] for a topic."""
    e = _entity(topic.scope)
    ph = _phrasings(topic.key, e, topic.keyword, topic.answer, topic.wrong)
    return [(variant, text, diff) for variant, (text, diff) in ph.items()]
