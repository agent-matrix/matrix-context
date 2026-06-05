"""LangGraph × Matrix Context.

A minimal agent graph that, each turn: **retrieves** memory with Matrix Context,
**generates** an answer, then **remembers** the turn — the build_pack/remember
loop expressed as a graph. Runs with a fake LLM (no API key); swap in any model.

    pip install matrix-context langgraph
    python tutorials/integrations/langgraph_demo.py
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from mc_ingest import SCOPE, build_context

CTX = build_context()


class State(TypedDict):
    question: str
    context: str
    answer: str


def fake_llm(question: str, context: str) -> str:
    """Stand-in model: grounded on the retrieved context (no API key needed)."""
    if "license" in question.lower() and "License" in context:
        return "PostgreSQL is released under the PostgreSQL License (free and open source)."
    if "acid" in question.lower():
        return "PostgreSQL provides ACID transactions: atomicity, consistency, isolation, durability."
    return "See the retrieved context above."


def retrieve(state: State) -> dict:
    # BEFORE the model: routed, budgeted context
    pack = CTX.build_pack(state["question"], scope=SCOPE, max_tokens=300)
    return {"context": pack.to_prompt()}


def generate(state: State) -> dict:
    return {"answer": fake_llm(state["question"], state["context"])}


def remember(state: State) -> dict:
    # AFTER the turn: keep what happened
    CTX.remember(state["question"], expert="session", scope=SCOPE, importance=0.3)
    CTX.remember(state["answer"], expert="semantic", scope=SCOPE, importance=0.4)
    return {}


def build_graph():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("remember", remember)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "remember")
    g.add_edge("remember", END)
    return g.compile()


def main() -> None:
    app = build_graph()
    for q in ["What license is PostgreSQL released under?", "What does ACID mean?"]:
        out = app.invoke({"question": q})
        print(f"Q: {q}\nA: {out['answer']}\n")


if __name__ == "__main__":
    main()
