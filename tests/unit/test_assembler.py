def test_pack_respects_budget_and_explains(ctx):
    pack = ctx.build_pack("what did we decide about MCP auth", max_tokens=40)
    assert pack.tokens <= 40
    assert pack.selected_experts
    for p in pack.items:
        assert set(p.breakdown) == {"relevance", "importance", "recency", "redundancy"}


def test_inspect_is_human_readable(ctx):
    text = ctx.inspect("what did we decide about MCP auth", max_tokens=100)
    assert "ROUTING:" in text and "PACK" in text
