"""Enumerations and the MVP expert taxonomy."""
from __future__ import annotations
from enum import Enum

# MVP expert taxonomy. These are typed memory partitions, NOT learned MoE experts.
EXPERTS = ("session", "profile", "semantic", "episodic", "document", "policy")


class Sensitivity(str, Enum):
    public = "public"
    internal = "internal"
    secret = "secret"


class ApprovalState(str, Enum):
    transient = "transient"        # ephemeral, never persisted long-term
    candidate = "candidate"        # proposed durable write, awaiting approval [v1]
    approved = "approved"          # durable, approved
