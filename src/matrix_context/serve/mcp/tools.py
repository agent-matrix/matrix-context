"""MCP tool definitions for Matrix Context.  [v1]

These describe the model-controlled tools the server exposes. The handlers call
straight into ContextManager. Kept declarative so the wrapper stays thin.
"""
from __future__ import annotations

TOOLS = [
    {"name": "context.remember", "description": "Write an auditable, approval-aware memory item."},
    {"name": "context.recall", "description": "Retrieve ranked context candidates."},
    {"name": "context.pack", "description": "Compose a token-budgeted, cited context pack."},
    {"name": "context.forget", "description": "TTL override, deletion or redaction."},
    {"name": "context.approve", "description": "Human approval flow for sensitive writes."},
    {"name": "context.router.explain", "description": "Explain expert selection and score contributions."},
]
