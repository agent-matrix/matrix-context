from matrix_context import ContextItem, HashingEmbedder
from matrix_context.retrieval.lexical import bm25_rank, tokenize
from matrix_context.retrieval.dense import dense_rank
from matrix_context.retrieval.fusion import rrf, hybrid_retrieve


def _items():
    emb = HashingEmbedder()
    items = [ContextItem(content="oauth pkce mcp auth decision", expert="policy"),
             ContextItem(content="user prefers local tools", expert="profile"),
             ContextItem(content="sqlite default backend", expert="semantic")]
    for it in items:
        it.embedding = emb.encode(it.content)
    return emb, items


def test_bm25_ranks_lexical_match_first():
    _, items = _items()
    ranked = bm25_rank("oauth auth", items)
    assert ranked[0][0] == items[0].id


def test_dense_and_fusion_run():
    emb, items = _items()
    q = emb.encode("oauth auth decision")
    assert dense_rank(q, items)[0][0] == items[0].id
    fused = hybrid_retrieve("oauth auth decision", q, items)
    assert max(fused, key=fused.get) == items[0].id


def test_rrf_combines_ranklists():
    a = [("x", 1.0), ("y", 0.5)]
    b = [("y", 1.0), ("x", 0.5)]
    fused = rrf([a, b])
    assert set(fused) == {"x", "y"}
