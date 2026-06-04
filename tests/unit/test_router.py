from matrix_context import HashingEmbedder
from matrix_context.routing.router import ContextRouter
from matrix_context.routing.rules import keyword_experts
from matrix_context import ContextItem


def test_router_returns_decision_with_scores():
    emb = HashingEmbedder()
    r = ContextRouter(emb)
    items = [ContextItem(content="policy rule about secrets", expert="policy")]
    items[0].embedding = emb.encode(items[0].content)
    d = r.route("what is the policy on secrets", items, top_experts=2)
    assert d.selected and d.scores and isinstance(d.reason, str)


def test_keyword_rules():
    assert "policy" in keyword_experts("is this allowed by policy")
    assert "profile" in keyword_experts("what is my preference")
