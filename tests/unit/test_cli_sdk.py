"""The simplified CLI and the beginner SDK do what the README promises.

Covers the 5-line quickstart through both surfaces:
    mc init / add / ask / inspect / list / forget   (CLI)
    mc.open(...).add(...).ask(...).inspect(...)      (SDK)
"""
from __future__ import annotations

import matrix_context as mc
from matrix_context import ContextManager
from matrix_context.cli.main import main


# --------------------------------------------------------------------------- #
# Beginner SDK
# --------------------------------------------------------------------------- #
def test_sdk_three_line_quickstart(tmp_path):
    memory = mc.open("demo", path=str(tmp_path / "demo.db"))
    memory.add("The team uses Postgres for production.")
    answer = memory.ask("What database do we use?")
    assert isinstance(answer, str) and "Postgres" in answer


def test_sdk_surface(tmp_path):
    memory = mc.open("bot", path=str(tmp_path / "bot.db"))
    item = memory.add("The user prefers concise answers.", expert="profile", scope="user:42")
    assert item.expert == "profile" and item.scope == "user:42"

    # ask / context_for return prompt-ready strings; pack returns the structure
    assert memory.ask("prefs?", scope="user:42") == memory.context_for("prefs?", scope="user:42")
    pack = memory.pack("prefs?", scope="user:42")
    assert pack.__class__.__name__ == "ContextPack"
    assert "ROUTING:" in memory.inspect("prefs?", scope="user:42")

    # chat loop helper
    memory.record_turn("hi", "hello there")
    assert len(memory.list()) == 3
    assert len(memory.list(expert="session")) == 1

    # forget
    assert memory.forget(item.id) is True
    assert memory.forget(item.id) is False

    # the advanced API is always reachable underneath
    assert isinstance(memory.ctx, ContextManager)


def test_sdk_open_uses_project_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    memory = mc.open("proj")
    memory.add("hello")
    assert (tmp_path / ".matrix-context" / "proj.db").exists()


# --------------------------------------------------------------------------- #
# Simplified CLI
# --------------------------------------------------------------------------- #
def test_cli_quickstart(tmp_path, capsys):
    db = str(tmp_path / "cli.db")

    assert main(["--db", db, "add", "The team uses Postgres for production.",
                 "--expert", "semantic"]) == 0
    assert "Added" in capsys.readouterr().out

    assert main(["--db", db, "ask", "What database do we use?"]) == 0
    assert "Postgres" in capsys.readouterr().out

    assert main(["--db", db, "inspect", "What database do we use?"]) == 0
    assert "ROUTING:" in capsys.readouterr().out

    assert main(["--db", db, "list"]) == 0
    assert "Postgres" in capsys.readouterr().out


def test_cli_init_and_discovery(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "demo"]) == 0
    out = capsys.readouterr().out
    assert "Initialized" in out
    assert (tmp_path / ".matrix-context" / "matrix-context.yaml").exists()

    # subsequent commands discover the project (no --db needed)
    assert main(["add", "We use Postgres."]) == 0
    capsys.readouterr()
    assert main(["ask", "database?"]) == 0
    assert "Postgres" in capsys.readouterr().out


def test_cli_forget(tmp_path, capsys):
    db = str(tmp_path / "f.db")
    main(["--db", db, "add", "ephemeral note"])
    item_id = capsys.readouterr().out.split()[1]
    assert main(["--db", db, "forget", item_id, "--yes"]) == 0
    assert "Forgot" in capsys.readouterr().out
    assert main(["--db", db, "list"]) == 0
    assert "(no items)" in capsys.readouterr().out


def test_cli_add_ingests_file(tmp_path, capsys):
    doc = tmp_path / "notes.txt"
    doc.write_text("Intro.\n\nPostgres is the production database.\n\nBackups nightly.")
    db = str(tmp_path / "d.db")
    assert main(["--db", db, "add", str(doc)]) == 0
    assert "chunk(s) from file" in capsys.readouterr().out
    assert main(["--db", db, "ask", "what is the production database?"]) == 0
    assert "Postgres" in capsys.readouterr().out


def test_cli_version_and_discovery_commands(tmp_path, capsys):
    db = str(tmp_path / "v.db")
    assert main(["version"]) == 0
    assert "matrix-context" in capsys.readouterr().out
    main(["--db", db, "add", "x", "--expert", "policy"])
    capsys.readouterr()
    assert main(["--db", db, "experts"]) == 0
    assert "policy" in capsys.readouterr().out
    assert main(["--db", db, "scopes"]) == 0
    assert "item(s)" in capsys.readouterr().out
