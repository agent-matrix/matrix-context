"""Runnable: python examples/quickstart.py"""
from matrix_context import ContextManager

ctx = ContextManager.create("example", path=":memory:")
ctx.remember("The user prefers local-first AI tools", expert="profile", importance=0.9)
ctx.remember("Decision: SQLite is the default backend", expert="semantic", importance=0.8)
ctx.remember("Policy: approval required before profile writes", expert="policy", importance=0.8)

pack = ctx.build_pack("What backend and what does the user prefer?", max_tokens=300)
print(pack.to_prompt())
print("\n--- inspect ---")
print(ctx.inspect("What backend and what does the user prefer?", max_tokens=300))
