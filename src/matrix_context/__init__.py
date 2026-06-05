"""Matrix Context — a local-first, inspectable Mixture-of-Contexts engine and
MCP server for agent memory."""
from .manager import ContextManager
from .config import Config
from .schema import ContextItem, ContextPack, RecallQuery, EXPERTS
from .embedding import HashingEmbedder, Embedder
from .simple import Memory, open  # beginner API: mc.open(...).add(...).ask(...)

__all__ = ["ContextManager", "Config", "ContextItem", "ContextPack",
           "RecallQuery", "EXPERTS", "HashingEmbedder", "Embedder",
           "Memory", "open", "CONTRACT_VERSION"]
__version__ = "0.1.0"

# MoC Contract version — the frozen public wire contract (JSON Schema + OpenAPI +
# MCP mapping under moc_contract/). Follows SemVer independently of the package
# version: wire-object/semantic changes bump this per moc_contract/compatibility.md.
CONTRACT_VERSION = "1.0.0"
