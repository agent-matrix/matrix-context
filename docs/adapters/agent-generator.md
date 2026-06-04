# agent-generator

When `agent-generator` is run with `--context-provider matrix-context`, it calls
`matrix_context.adapters.agent_generator.emit_template` to wire a real memory
layer into the generated project — no hand-editing required.

```bash
agent-generator "Research assistant with persistent governed memory" \
  -f crewai --context-provider matrix-context --mcp -o team.py
```

Two variants, selected by the `--mcp` flag:

- **in-process** (default): a local `ContextManager` backed by a default SQLite
  store. The generated `matrix_memory.py` calls `build_pack` *before* each model
  call (`build_context`) and `remember` *after* each turn (`record_turn`), so the
  agent actually accumulates and uses memory.
- **MCP** (`--mcp`): emits `mcp.json` launching `matrix-context serve --transport
  stdio` instead of the in-process client (with a local fallback so the project
  still runs offline).

The emitter is framework-aware for `react`, `crewai`, and `langgraph` — the core
`ContextManager` wiring is identical; only the call-site shape differs. Example
scopes are derived from the agent's purpose (a `policy` scope is added when the
purpose hints at governance).

```python
from matrix_context.adapters.agent_generator import emit_template

t = emit_template("Research assistant", framework="crewai")
print(t.files["matrix_memory.py"])  # imports ContextManager, SQLite path, build_pack
```
