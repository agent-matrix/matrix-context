"""Matrix Context — a local-first, inspectable Mixture-of-Contexts engine and
MCP server for agent memory."""
from .manager import ContextManager
from .config import Config
from .schema import ContextItem, ContextPack, RecallQuery, EXPERTS
from .embedding import HashingEmbedder, Embedder

__all__ = ["ContextManager", "Config", "ContextItem", "ContextPack",
           "RecallQuery", "EXPERTS", "HashingEmbedder", "Embedder"]
__version__ = "0.1.0"
