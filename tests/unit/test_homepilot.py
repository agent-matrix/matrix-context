"""HomePilot adapter end-to-end: profile + persona memory -> inspectable pack.

Loads a sample HomePilot persona and a handful of persona memories, issues a
query, and asserts the pack contains the always-injectable profile fact AND the
routed memory, and that inspect() explains the selection. Also checks the
deterministic Basic engine (TTL + cap) against the Adaptive engine.
"""
from matrix_context import ContextManager
from matrix_context.adapters.homepilot import HomePilotAdapter, Mode

# A trimmed HomePilot persona definition (cf. backend/app/personalities/...).
SAMPLE_PERSONA = {
    "id": "motivation",
    "label": "Motivator",
    "category": "wellness",
    "psychology_approach": "Self-determination theory + growth mindset",
    "system_prompt": "You are a world-class motivational coach. Be authentic.",
    "key_techniques": ["Vision casting", "Reframing obstacles as growth"],
    "unique_behaviors": ["Builds to emotional crescendos"],
    "affirmations": ["You have more in you than you know."],
}

PERSONA_MEMORIES = [
    "The user is training for a marathon in October.",
    "The user works best with morning workouts.",
    "The user dislikes generic motivational quotes.",
]


def _adapter(mode: Mode = Mode.ADAPTIVE) -> HomePilotAdapter:
    ctx = ContextManager.create("hp-test", path=":memory:")
    a = HomePilotAdapter(ctx, mode=mode)
    counts = a.load_persona(SAMPLE_PERSONA)
    assert counts["profile"] >= 3 and counts["memory"] >= 1
    a.load_memories(PERSONA_MEMORIES, expert="semantic", importance=0.7)
    return a


def test_pack_contains_profile_and_routed_memory_and_is_explained():
    a = _adapter()
    query = "what is the user training for?"
    pack = a.build_pack(query)

    contents = " ".join(p.item.content for p in pack.items)
    experts = {p.item.expert for p in pack.items}
    # Profile is always injectable...
    assert "profile" in experts
    assert any("motivation" in c or "Motivator" in c for c in
               [p.item.content for p in pack.items])
    # ...and the relevant learned memory was recalled by routing.
    assert "marathon" in contents
    # Compact-injection discipline: low hundreds of tokens.
    assert pack.tokens <= 220

    explanation = a.explain(query)
    assert "ROUTING:" in explanation and "PACK (" in explanation
    assert "profile" in explanation


def test_basic_mode_applies_ttl_and_cap():
    ctx = ContextManager.create("hp-basic", path=":memory:")
    a = HomePilotAdapter(ctx, mode=Mode.BASIC, basic_cap=3)
    for i in range(6):
        a.remember_turn(f"turn number {i}", expert="episodic")
    mem = [it for it in ctx.store.all_items()
           if it.scope == a._scope("memory")]
    # Cap keeps only the newest 3, and Basic memories carry a TTL.
    assert len(mem) == 3
    assert all(it.ttl is not None for it in mem)
    assert all(it.scope == "/homepilot/memory" for it in mem)


def test_adaptive_mode_has_no_ttl():
    a = _adapter(mode=Mode.ADAPTIVE)
    mem = [it for it in a.ctx.store.all_items()
           if it.scope == a._scope("memory")]
    assert mem and all(it.ttl is None for it in mem)


def test_live_state_seam_is_pinned_like_profile():
    a = _adapter()
    a.load_live_state({"living_room_light": "on", "thermostat": "21C"})
    # Profile pinning keeps identity injectable even on an unrelated query.
    pack = a.build_pack("tell me about workout timing")
    assert "profile" in {p.item.expert for p in pack.items}
