import time
from matrix_context import ContextItem


def test_item_defaults_and_id():
    it = ContextItem(content="hello world", expert="semantic")
    assert it.id.startswith("ctx_")
    assert it.is_live()
    assert it.approx_tokens() >= 1


def test_ttl_expiry():
    it = ContextItem(content="x", expert="session", ttl=10, created_at=time.time() - 100)
    assert not it.is_live()
