# HomePilot (MVP)

The first real consumer, and the path to live gold signal. The adapter preserves
HomePilot's two existing distinctions rather than replacing its memory:

- **Profile vs. learned memory.** Profile fields map to the `profile` expert and
  are *always injectable* (pinned into every pack). Persona memories map to the
  `semantic` / `episodic` experts and are recalled by routing.
- **Two engines.** `Mode.BASIC` is deterministic (per-memory TTL + a per-scope
  cap, newest-wins). `Mode.ADAPTIVE` uses the engine's recency decay + importance
  weighting; consolidation is deferred to the v1 lifecycle module.

Compact-injection discipline is respected — `build_pack` defaults to a
low-hundreds-of-tokens budget (220). Device / persona live state is exposed
through a `live_state` expert seam that pins like profile until the live-state
expert lands in v1. Every selection is explainable via `explain()` (`inspect()`).

```python
from matrix_context import ContextManager
from matrix_context.adapters.homepilot import HomePilotAdapter, Mode

ctx = ContextManager.create("homepilot", path="homepilot.db")
hp = HomePilotAdapter(ctx, mode=Mode.ADAPTIVE)
hp.load_persona(persona_dict)                 # profile + semantic split
hp.load_memories(["The user runs marathons"]) # routed memory
pack = hp.build_pack("what does the user train for?")  # profile pinned + memory
print(hp.explain("what does the user train for?"))     # why each item was chosen
```

The framing: HomePilot treats Matrix Context as an externalized, inspectable
context plane it can hand off to other agents or reach over MCP — not a black box
that replaces what already works.
