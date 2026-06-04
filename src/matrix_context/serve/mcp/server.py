"""MCP server entry point.  [v1 — skeleton]

Wraps a ContextManager and exposes tools/resources/prompts over the chosen
transport. Built only AFTER the engine + eval prove the routed-pack advantage.
Requires the `mcp` extra.
"""
from __future__ import annotations

from .tools import TOOLS
from .resources import RESOURCE_TEMPLATES
from .prompts import PROMPTS


def serve(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8088,
          name: str = "matrix-context"):  # pragma: no cover - [v1]
    raise NotImplementedError(
        "MCP server is a v1 component. Tools/resources/prompts are declared in "
        "this package; wire them to the `mcp` SDK once the engine is proven.")
