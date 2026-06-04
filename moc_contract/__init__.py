"""MoC Contract v1 — the frozen public wire contract for Matrix Context.

This package is the *standard*, separate from any one implementation: a set of
JSON Schema (Draft 2020-12) definitions for the wire objects, an OpenAPI 3.1
description of the HTTP surface, an MCP mapping, a SemVer compatibility policy,
and an executable conformance suite. A REST/MCP server is "MoC v1 compatible" if
it passes :mod:`moc_contract.conformance` against the frozen schemas.

REST is the source-of-truth contract; the MCP mapping is the interop binding.
"""
from __future__ import annotations

CONTRACT_VERSION = "1.0.0"

# The wire objects frozen by v1 (see schemas/ and compatibility.md).
OBJECTS = [
    "memory_item", "score_breakdown", "packed_item", "dropped_item",
    "expert_score", "error",
    "remember_request", "query_request", "forget_request",
    "item_response", "items_response", "remember_response", "forget_response",
    "health_response", "version_response", "experts_response", "scopes_response",
    "pack_response", "inspect_response", "router_explain_response",
]
