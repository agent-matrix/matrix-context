"""Benchmark taxonomy: experts, context types, domains, and routing priors.

These are the *benchmark's* typed partitions (8 experts, 11 types, 6 domains).
They are intentionally richer than the core engine's 6-expert MVP taxonomy: the
benchmark is where a larger taxonomy is exercised before any of it is promoted
into the engine. The hybrid router (see runners.MoCRouter) uses the keyword and
type priors declared here in addition to embedding centroids.
"""
from __future__ import annotations

from typing import Dict, List

# 8 context experts (typed memory partitions).
EXPERTS: List[str] = [
    "user_memory",
    "project_memory",
    "document_rag",
    "code_context",
    "session_memory",
    "decision_memory",
    "policy_rules",
    "tool_history",
]

# 11 context types.
TYPES: List[str] = [
    "fact", "preference", "goal", "decision", "rule", "document",
    "code", "episode", "summary", "tool_result", "profile",
]

# Seed descriptions for cold-start centroids (one per expert).
EXPERT_DESCRIPTIONS: Dict[str, str] = {
    "user_memory": "user preferences profile identity persona settings boundaries likes",
    "project_memory": "project architecture design notes goals roadmap milestones decisions context",
    "document_rag": "documents whitepaper manuals reference material specs files pages docs",
    "code_context": "source code functions modules repository implementation where defined classes",
    "session_memory": "current conversation recent session thread continuity dialogue messages",
    "decision_memory": "decisions chosen approach why we decided rationale trade-offs selected default",
    "policy_rules": "policy rules compliance allowed forbidden approval security guardrails legal pii",
    "tool_history": "tool runs command outputs results logs executions actions invoked produced",
}

# Canonical expert for each type (used as a type prior in the hybrid router).
TYPE_TO_EXPERT: Dict[str, str] = {
    "fact": "project_memory",
    "preference": "user_memory",
    "goal": "project_memory",
    "decision": "decision_memory",
    "rule": "policy_rules",
    "document": "document_rag",
    "code": "code_context",
    "episode": "session_memory",
    "summary": "session_memory",
    "tool_result": "tool_history",
    "profile": "user_memory",
}

# Keyword priors: tokens that, when present in a query, lean toward an expert.
KEYWORD_PRIORS: Dict[str, List[str]] = {
    "user_memory": ["prefer", "preference", "user", "persona", "profile", "like",
                    "respond", "tone", "assistant"],
    "project_memory": ["project", "architecture", "roadmap", "goal", "milestone",
                       "design", "plan"],
    "document_rag": ["document", "whitepaper", "manual", "spec", "say", "section",
                     "limitation", "paper"],
    "code_context": ["function", "code", "implement", "module", "class", "where",
                     "file", "repository", "defined"],
    "session_memory": ["session", "conversation", "recent", "earlier", "last",
                       "thread", "we discussed"],
    "decision_memory": ["decide", "decision", "chose", "choose", "why", "default",
                        "rationale", "selected", "agreed"],
    "policy_rules": ["policy", "rule", "allowed", "can the agent", "should", "store",
                     "sensitive", "pii", "secret", "compliance", "approval"],
    "tool_history": ["tool", "command", "output", "result", "ran", "produced",
                     "eval", "benchmark", "log"],
}

# The six agentic-memory domains the benchmark spans.
DOMAINS: List[str] = [
    "project_architecture",
    "user_persona",
    "code_context",
    "policy_rules",
    "tool_session",
    "document_rag",
]
