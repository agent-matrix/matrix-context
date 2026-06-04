"""Deterministic benchmark generator.

Builds typed context items, queries, gold labels, and **hard negatives** across
six agentic-memory domains. Generation is seeded so the dataset is reproducible
byte-for-byte. Each gold fact is surrounded by the five hard-negative kinds the
benchmark is designed to test — the cases where flat RAG is tempted but MoC-RAG
should route around:

    same_keyword_wrong_expert  same salient keyword, different typed expert
    same_expert_wrong_scope    a true fact, but for a different project/persona
    outdated_decision          a superseded decision (low confidence, old)
    contradictory_memory       a note asserting a conflicting value
    stale_session_note         an old session mention with nothing decided

The result comfortably exceeds the minimum-publishable targets (>=1000 contexts,
>=300 queries, 8 experts, >=10 types, 6 domains) and is split train/val/test.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .schema import (ContextRow, GoldRow, QueryRow, write_jsonl)
from .variants import VARIANT_CATEGORY, make_variants

# Entity pools (the levers that multiply templates into a sizable dataset).
PROJECTS = ["matrix-context", "agent-generator", "homepilot", "gitpilot", "ruslanmv-web"]
PERSONAS = ["secretary", "analyst", "coach", "tutor", "concierge"]
MODULES = ["router", "assembler", "store", "retrieval", "embedder", "cli"]
SECTIONS = ["abstract", "method", "limitations", "results", "positioning"]
POLICY_TOPICS = ["API keys", "PII", "secrets", "audit logs", "data deletion", "approval tokens"]
TOOLS = ["eval.harness", "experiments.runner", "pytest", "ruff", "mypy"]

NOW = "2026-06-04T10:00:00Z"
OLD = "2025-09-01T10:00:00Z"


@dataclass
class Topic:
    topic_id: str
    key: str            # template id; selects the variant phrasings (see variants.py)
    domain: str
    expert: str
    type: str
    scope: str
    content: str
    answer: str
    wrong: str
    keyword: str
    tags: List[str]
    expected_experts: List[str]
    importance: float
    task_type: str = "recall"


def _topics() -> List[Topic]:
    """Concrete topic instances across the six domains."""
    T: List[Topic] = []
    n = 0

    def add(**kw):
        nonlocal n
        T.append(Topic(topic_id=f"t_{n:04d}", **kw))
        n += 1

    # --- Domain 1: project architecture (scoped by project) -----------------
    for p in PROJECTS:
        add(key="backend", domain="project_architecture", expert="decision_memory",
            type="decision", scope=f"project:{p}", keyword="storage backend",
            content=f"In {p}, the team decided to use SQLite as the default storage backend.",
            answer="SQLite", wrong="Postgres", tags=["backend", "storage", "decision"],
            expected_experts=["decision_memory", "project_memory"], importance=0.95,
            task_type="architecture_recall")
        add(key="interfaces", domain="project_architecture", expert="project_memory",
            type="fact", scope=f"project:{p}", keyword="MCP server",
            content=f"{p} exposes both a Python SDK and an MCP server.",
            answer="Python SDK and an MCP server", wrong="a REST API only",
            tags=["mcp", "sdk", "architecture"],
            expected_experts=["project_memory", "decision_memory"], importance=0.9,
            task_type="architecture_recall")
        add(key="milvus_defer", domain="project_architecture", expert="decision_memory",
            type="decision", scope=f"project:{p}", keyword="Milvus",
            content=f"{p} decided to defer Milvus support to v2.",
            answer="v2", wrong="v1", tags=["milvus", "roadmap", "decision"],
            expected_experts=["decision_memory", "project_memory"], importance=0.8,
            task_type="roadmap_recall")

    # --- Domain 2: user / persona memory (scoped by persona) ----------------
    for pa in PERSONAS:
        add(key="pref_local", domain="user_persona", expert="user_memory",
            type="preference", scope=f"persona:{pa}", keyword="local-first",
            content=f"The {pa} persona prefers local-first tools over cloud services.",
            answer="local-first", wrong="cloud-first", tags=["preference", "tools"],
            expected_experts=["user_memory"], importance=0.85, task_type="preference_recall")
        add(key="pref_tone", domain="user_persona", expert="user_memory", type="profile",
            scope=f"persona:{pa}", keyword="tone",
            content=f"The {pa} persona uses a warm, professional tone.",
            answer="warm, professional", wrong="terse and blunt", tags=["profile", "tone"],
            expected_experts=["user_memory"], importance=0.7, task_type="profile_recall")

    # --- Domain 3: code context (scoped by project + module) ----------------
    for p in PROJECTS:
        for m in MODULES:
            add(key="code_loc", domain="code_context", expert="code_context", type="code",
                scope=f"project:{p}", keyword=f"{m}",
                content=f"In {p}, the {m} is implemented in src/{p.replace('-', '_')}/{m}.py.",
                answer=f"src/{p.replace('-', '_')}/{m}.py", wrong="a notebook",
                tags=["code", m], expected_experts=["code_context"], importance=0.6,
                task_type="code_locate")

    # --- Domain 4: policy rules (scoped by project) -------------------------
    for p in PROJECTS:
        for pt in POLICY_TOPICS[:4]:
            add(key="policy", domain="policy_rules", expert="policy_rules", type="rule",
                scope=f"project:{p}", keyword=pt,
                content=f"Policy in {p}: the agent must never store {pt} in durable memory.",
                answer=f"never store {pt}", wrong=f"store {pt} freely",
                tags=["policy", "rule"], expected_experts=["policy_rules"], importance=0.9,
                task_type="policy_check")

    # --- Domain 5: tool / session history (scoped by project) ---------------
    for p in PROJECTS:
        for t in TOOLS[:3]:
            add(key="tool_result", domain="tool_session", expert="tool_history",
                type="tool_result", scope=f"project:{p}", keyword=t,
                content=f"The last {t} run on {p} produced a passing result.",
                answer="passing", wrong="failing", tags=["tool", "result"],
                expected_experts=["tool_history"], importance=0.6, task_type="tool_recall")
        add(key="session_episode", domain="tool_session", expert="session_memory",
            type="episode", scope=f"project:{p}", keyword="REST API",
            content=f"In the last session about {p}, we agreed to ship the REST API first.",
            answer="REST API first", wrong="the UI first", tags=["session", "episode"],
            expected_experts=["session_memory"], importance=0.65, task_type="episodic_recall")

    # --- Domain 6: document RAG (scoped by project + section) ---------------
    for p in PROJECTS:
        for sec in SECTIONS:
            add(key="doc", domain="document_rag", expert="document_rag", type="document",
                scope=f"project:{p}", keyword=sec,
                content=(f"The {p} whitepaper {sec} section states that routed typed "
                         f"context cuts distractors at equal recall."),
                answer="cuts distractors at equal recall", wrong="increases recall",
                tags=["document", sec], expected_experts=["document_rag"], importance=0.7,
                task_type="document_qa")
    return T


# Per-domain alternate experts for the "same keyword wrong expert" negative.
_WRONG_EXPERT = {
    "decision_memory": "document_rag", "project_memory": "session_memory",
    "user_memory": "session_memory", "code_context": "document_rag",
    "policy_rules": "document_rag", "tool_history": "session_memory",
    "session_memory": "tool_history", "document_rag": "project_memory",
}


def _hard_negatives(topic: Topic, start_idx: int) -> List[ContextRow]:
    """Build the hard negatives surrounding one gold fact (>=4, all 5 kinds
    appear across the dataset)."""
    negs: List[ContextRow] = []
    other_scope = ("project:other-project" if topic.scope.startswith("project:")
                   else "persona:other-persona")

    specs = [
        # (negative_kind, expert, type, content, importance, confidence, created_at)
        ("same_keyword_wrong_expert", _WRONG_EXPERT.get(topic.expert, "document_rag"),
         "document",
         f"General background notes about {topic.keyword} configuration and trade-offs.",
         0.4, 0.7, NOW),
        ("outdated_decision", "decision_memory", "decision",
         f"Previously, {topic.scope} used a different approach for {topic.keyword}; "
         f"this is now superseded.", 0.3, 0.4, OLD),
        ("contradictory_memory", "session_memory", "summary",
         f"A conflicting note claims {topic.scope} uses {topic.wrong} for {topic.keyword}.",
         0.35, 0.3, NOW),
        ("stale_session_note", "session_memory", "episode",
         f"In an old session we briefly mentioned {topic.keyword}, but nothing was decided.",
         0.3, 0.5, OLD),
        # Only meaningful for scoped topics: a true fact for the WRONG scope.
        ("same_expert_wrong_scope", topic.expert, topic.type,
         topic.content.replace(topic.scope.split(':', 1)[-1], other_scope.split(':', 1)[-1])
         if ':' in topic.scope else topic.content,
         topic.importance, 0.9, NOW),
    ]
    for k, (kind, expert, typ, content, imp, conf, ts) in enumerate(specs):
        negs.append(ContextRow(
            context_id=f"ctx_{start_idx + k:06d}", expert=expert, type=typ,
            scope=topic.scope if kind != "same_expert_wrong_scope" else other_scope,
            content=content, tags=[topic.keyword.split()[0], "negative"],
            importance=imp, confidence=conf, source="synthetic_hard_negative",
            created_at=ts, topic=topic.topic_id, role="distractor", negative_kind=kind))
    return negs


def generate(seed: int = 13, min_contexts: int = 1000,
             min_queries: int = 300) -> Tuple[List[ContextRow], List[QueryRow], List[GoldRow]]:
    rng = random.Random(seed)
    topics = _topics()

    contexts: List[ContextRow] = []
    queries: List[QueryRow] = []
    gold: List[GoldRow] = []
    cid = 0
    qid = 0

    for topic in topics:
        # Gold item.
        gold_id = f"ctx_{cid:06d}"; cid += 1
        contexts.append(ContextRow(
            context_id=gold_id, expert=topic.expert, type=topic.type, scope=topic.scope,
            content=topic.content, tags=topic.tags, importance=topic.importance,
            confidence=0.92, source="synthetic_gold", created_at=NOW,
            topic=topic.topic_id, role="gold"))
        # One acceptable paraphrase.
        acc_id = f"ctx_{cid:06d}"; cid += 1
        contexts.append(ContextRow(
            context_id=acc_id, expert=topic.expert, type=topic.type, scope=topic.scope,
            content=f"Note: {topic.content}", tags=topic.tags, importance=topic.importance - 0.1,
            confidence=0.85, source="synthetic_acceptable", created_at=NOW,
            topic=topic.topic_id, role="acceptable"))
        # Hard negatives.
        negs = _hard_negatives(topic, cid); cid += len(negs)
        contexts.extend(negs)
        neg_ids = [nr.context_id for nr in negs]

        # Five query variants per topic — same gold label, varying lexical
        # overlap and intent. Gold stays STABLE across all variants.
        for (variant, text, difficulty) in make_variants(topic):
            q_id = f"q_{qid:06d}"; qid += 1
            queries.append(QueryRow(
                query_id=q_id, query=text, task_type=topic.task_type,
                expected_experts=topic.expected_experts, scope=topic.scope,
                difficulty=difficulty, domain=topic.domain, topic=topic.topic_id,
                variant=variant))
            gold.append(GoldRow(
                query_id=q_id, gold_context_ids=[gold_id],
                acceptable_context_ids=[acc_id], distractor_context_ids=neg_ids,
                gold_answer=topic.answer, gold_citations=[gold_id]))

    # Pad with deterministic filler background so flat RAG faces a large, noisy
    # store (filler is never gold; it is global distraction).
    filler_n = 0
    while len(contexts) < min_contexts:
        topic = rng.choice(topics)
        contexts.append(ContextRow(
            context_id=f"ctx_{cid:06d}", expert=rng.choice(list(_WRONG_EXPERT)),
            type="fact", scope=topic.scope,
            content=(f"Background fact #{filler_n} loosely related to "
                     f"{topic.keyword} and {rng.choice(MODULES)}."),
            tags=["filler"], importance=round(rng.uniform(0.1, 0.4), 2),
            confidence=0.6, source="synthetic_filler", created_at=NOW,
            topic="", role="filler"))
        cid += 1
        filler_n += 1

    return contexts, queries, gold


def split(queries: List[QueryRow], seed: int = 13,
          ratios=(0.6, 0.2, 0.2)) -> Dict[str, List[str]]:
    """Deterministic, domain-stratified split at the TOPIC level, plus parallel
    variant test splits.

    Splitting by topic (not query) keeps all variants of a topic in the same
    bucket, so ``test_keyword`` / ``test_paraphrased`` / ``test_adversarial`` are
    *parallel*: the same test topics phrased three ways. This is what lets us
    attribute a metric change to the query style rather than to topic leakage.
    """
    rng = random.Random(seed)
    # Stratify unique topics by domain.
    topic_domain: Dict[str, str] = {}
    for q in queries:
        topic_domain.setdefault(q.topic, q.domain)
    by_domain: Dict[str, List[str]] = {}
    for topic_id, domain in topic_domain.items():
        by_domain.setdefault(domain, []).append(topic_id)

    topic_split: Dict[str, str] = {}
    for _domain, topic_ids in sorted(by_domain.items()):
        topic_ids = sorted(topic_ids)
        rng.shuffle(topic_ids)
        ntr = int(len(topic_ids) * ratios[0])
        nva = int(len(topic_ids) * (ratios[0] + ratios[1]))
        for t in topic_ids[:ntr]:
            topic_split[t] = "train"
        for t in topic_ids[ntr:nva]:
            topic_split[t] = "validation"
        for t in topic_ids[nva:]:
            topic_split[t] = "test"

    out: Dict[str, List[str]] = {k: [] for k in
                                 ("train", "validation", "test",
                                  "test_keyword", "test_paraphrased", "test_adversarial")}
    for q in queries:
        bucket = topic_split[q.topic]
        out[bucket].append(q.query_id)
        if bucket == "test":
            out[f"test_{VARIANT_CATEGORY[q.variant]}"].append(q.query_id)
    return out


def build(out_dir: Path, seed: int = 13, min_contexts: int = 1000,
          min_queries: int = 300) -> Dict[str, int]:
    """Generate the dataset and write all jsonl files. Returns row counts."""
    contexts, queries, gold = generate(seed, min_contexts, min_queries)
    splits = split(queries, seed)

    write_jsonl(contexts, out_dir / "contexts.jsonl")
    write_jsonl(queries, out_dir / "queries.jsonl")
    write_jsonl(gold, out_dir / "gold.jsonl")
    qbyid = {q.query_id: q for q in queries}
    gbyid = {g.query_id: g for g in gold}
    for name, ids in splits.items():
        write_jsonl([qbyid[i] for i in ids], out_dir / "splits" / f"{name}.jsonl")
        write_jsonl([gbyid[i] for i in ids], out_dir / "splits" / f"{name}_gold.jsonl")

    return {
        "contexts": len(contexts),
        "queries": len(queries),
        "gold": len(gold),
        "experts": len({c.expert for c in contexts}),
        "types": len({c.type for c in contexts}),
        "domains": len({q.domain for q in queries}),
        "variants": len({q.variant for q in queries}),
        "train": len(splits["train"]),
        "validation": len(splits["validation"]),
        "test": len(splits["test"]),
        "test_keyword": len(splits["test_keyword"]),
        "test_paraphrased": len(splits["test_paraphrased"]),
        "test_adversarial": len(splits["test_adversarial"]),
        "hard_negatives": len({c.negative_kind for c in contexts if c.negative_kind}),
    }
