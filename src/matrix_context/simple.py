"""The beginner-friendly SDK — Matrix Context in three lines.

    import matrix_context as mc
    memory = mc.open("demo")
    memory.add("The team uses Postgres for production.")
    print(memory.ask("What database do we use?"))

This is a thin, friendly wrapper over :class:`~matrix_context.manager.ContextManager`
(the advanced API, which is unchanged). Beginners never need to learn
``ContextManager``, ``build_pack`` or ``remember`` on day one; agent developers
get a clean ``context_for`` / ``record_turn`` chat loop; researchers keep the
full engine underneath via ``memory.ctx``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # avoid importing the engine at module import time
    from .manager import ContextManager
    from .schema.item import ContextItem
    from .schema.pack import ContextPack

__all__ = ["Memory", "open"]


class Memory:
    """A friendly handle on one Matrix Context store.

    Wraps a :class:`ContextManager`. The underlying manager is always available
    as ``memory.ctx`` if you need the full advanced API.
    """

    def __init__(self, ctx: "ContextManager") -> None:
        self.ctx = ctx

    # -- write ----------------------------------------------------------- #
    def add(self, text: str, expert: str = "semantic", scope: str = "/",
            importance: float = 0.5, tags=None, ttl: Optional[float] = None) -> "ContextItem":
        """Remember a piece of text. The one method beginners need to write."""
        return self.ctx.remember(text, expert=expert, scope=scope,
                                 importance=importance, tags=tuple(tags or ()), ttl=ttl)

    # Friendly aliases (documented surface stays `add`).
    def remember(self, text: str, **kw) -> "ContextItem":
        return self.add(text, **kw)

    def save(self, text: str, **kw) -> "ContextItem":
        return self.add(text, **kw)

    # -- read ------------------------------------------------------------ #
    def ask(self, query: str, scope: str = "/", max_tokens: int = 400) -> str:
        """Return a prompt-ready context string for ``query`` (for humans)."""
        return self.ctx.build_pack(query, scope=scope, max_tokens=max_tokens).to_prompt()

    def context_for(self, query: str, scope: str = "/", max_tokens: int = 400) -> str:
        """Same as :meth:`ask` — reads naturally inside an agent chat loop."""
        return self.ask(query, scope=scope, max_tokens=max_tokens)

    def pack(self, query: str, scope: str = "/", max_tokens: int = 400) -> "ContextPack":
        """Return the structured :class:`ContextPack` (for agent code)."""
        return self.ctx.build_pack(query, scope=scope, max_tokens=max_tokens)

    def inspect(self, query: str, scope: str = "/", max_tokens: int = 400) -> str:
        """Explain *why* memory was selected for ``query``."""
        return self.ctx.inspect(query, scope=scope, max_tokens=max_tokens)

    def list(self, scope: Optional[str] = None, expert: Optional[str] = None) -> list:
        """List stored items, optionally filtered by scope and/or expert."""
        return self.ctx.items(scope=scope, expert=expert)

    # -- forget ---------------------------------------------------------- #
    def forget(self, item_id: str) -> bool:
        """Delete an item by id. Returns True if it existed."""
        return self.ctx.forget(item_id)

    # -- chat loop ------------------------------------------------------- #
    def record_turn(self, user: str, assistant: str, scope: str = "/",
                    importance: float = 0.4) -> None:
        """Persist one conversational turn (user + assistant) to ``session``/``semantic``."""
        self.add(user, expert="session", scope=scope, importance=importance)
        self.add(assistant, expert="semantic", scope=scope, importance=importance)

    # -- serving --------------------------------------------------------- #
    def serve(self, host: str = "127.0.0.1", port: int = 8088) -> None:
        """Run the REST API (v1) + Console UI backed by this memory (blocking)."""
        from .serve.rest.app import serve as serve_rest
        serve_rest(host=host, port=port, manager=self.ctx)

    def ui(self, host: str = "127.0.0.1", port: int = 8088) -> None:
        """Open the Console UI (Playground) in a browser and serve it (blocking)."""
        import threading
        import webbrowser
        url = f"http://{host}:{port}/ui"
        print(f"Opening the Matrix Context Playground at {url}")
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        self.serve(host=host, port=port)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        n = len(self.ctx.store.all_items())
        return f"<Memory name={self.ctx.config.name!r} items={n}>"


def open(name: str = "default", path: Optional[str] = None) -> Memory:
    """Open (or create) a memory store by name. The entry point for beginners.

        import matrix_context as mc
        memory = mc.open("demo")

    By default the store lives at ``.matrix-context/<name>.db`` so projects stay
    self-contained. Pass ``path=`` to choose an explicit location.
    """
    from .manager import ContextManager

    if path is None:
        from pathlib import Path

        from .cli import project as _project
        root = _project.find_root()
        base = (root / _project.PROJECT_DIR) if root else Path(_project.PROJECT_DIR)
        base.mkdir(parents=True, exist_ok=True)
        path = str(base / f"{name}.db")
    return Memory(ContextManager.create(name, path=path))
