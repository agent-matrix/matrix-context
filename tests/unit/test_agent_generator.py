"""agent-generator integration: the emitted memory layer is real & usable.

Proves the engine is usable from generated code — the client imports
ContextManager, references a SQLite path, and calls build_pack — for both the
in-process and MCP variants and across every supported framework.
"""
import pytest

from matrix_context.adapters.agent_generator import (
    FRAMEWORKS,
    IN_PROCESS,
    MCP,
    emit_template,
)


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_in_process_template_is_wired(framework):
    t = emit_template("Research assistant with persistent memory",
                      framework=framework)
    code = t.code
    assert t.variant == IN_PROCESS
    # The three hard acceptance checks from the brief:
    assert "from matrix_context import ContextManager" in code
    assert ".matrix-context.db" in code  # references a SQLite path
    assert "build_pack(" in code         # calls build_pack before model calls
    # The two calls that matter are both present.
    assert "ctx.remember(" in code
    assert "def build_context(" in code and "def record_turn(" in code


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_mcp_template_emits_stdio_launch_config(framework):
    t = emit_template("Governed research assistant", framework=framework, mcp=True)
    assert t.variant == MCP
    cfg = t.config
    assert "matrix-context" in cfg
    assert "serve" in cfg and "--transport" in cfg and "stdio" in cfg
    # Even the MCP variant ships a runnable local client (offline fallback).
    assert "from matrix_context import ContextManager" in t.code
    assert "build_pack(" in t.code


def test_scopes_are_purpose_aware():
    governed = emit_template("Audit-log compliance assistant", framework="react")
    assert "policy" in governed.scopes
    plain = emit_template("Friendly chat helper", framework="react")
    assert "policy" not in plain.scopes
    assert {"profile", "semantic", "episodic"} <= set(plain.scopes)


def test_emitted_in_process_client_executes_and_remembers(tmp_path):
    """The generated module must run: bootstrap, record a turn, recall it."""
    t = emit_template("Note taker", framework="react",
                      store_path=str(tmp_path / "mem.matrix-context.db"))
    ns: dict = {}
    exec(compile(t.code, "matrix_memory.py", "exec"), ns)
    ns["bootstrap"]()
    ns["record_turn"]("The user prefers Postgres for audit logs.",
                      "Noted: Postgres for audit logs.")
    pack = ns["build_context"]("what database for audit logs?")
    assert "Postgres" in pack


def test_unknown_framework_rejected():
    with pytest.raises(ValueError):
        emit_template("x", framework="autogen")
