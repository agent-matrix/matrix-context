import pytest
from matrix_context import ContextManager


@pytest.fixture
def ctx():
    c = ContextManager.create("test", path=":memory:")
    c.remember("Decision: use OAuth 2.1 with PKCE for MCP HTTP clients", expert="policy", importance=0.9)
    c.remember("The user prefers local-first tools", expert="profile", importance=0.9)
    c.remember("Decision: SQLite is the default backend", expert="semantic", importance=0.8)
    c.remember("On 2026-05-02 we agreed to defer Milvus to v2", expert="episodic", importance=0.6)
    return c
