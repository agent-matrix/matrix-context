import time

from matrix_context.embedding.hashing import HashingEmbedder
from matrix_context.lifecycle.consolidation import consolidate
from matrix_context.manager import ContextManager
from matrix_context.schema.item import ContextItem


def test_managed_write_deduplicates(tmp_path):
    ctx = ContextManager.create(
        "t", path=str(tmp_path / "m.db"), embedder=HashingEmbedder()
    )
    a = ctx.remember_managed("The service uses Postgres.", expert="semantic")
    b = ctx.remember_managed("  the service uses postgres.  ", expert="semantic")
    assert a.id == b.id


def test_supersession_keeps_old_item(tmp_path):
    ctx = ContextManager.create(
        "t", path=str(tmp_path / "m.db"), embedder=HashingEmbedder()
    )
    old = ctx.remember_managed("Deploy window is Friday", expert="semantic")
    new = ctx.remember_managed(
        "Deploy window is Monday", expert="semantic", supersedes=old.id
    )
    assert "superseded" in ctx.store.get(old.id).tags
    assert f"supersedes:{old.id}" in new.tags


def test_consolidation_emits_procedural():
    old = time.time() - 10 * 86400
    items = [
        ContextItem(
            "retry with backoff worked",
            "episodic",
            created_at=old,
            importance=0.4,
        ),
        ContextItem(
            "health probe before retry worked",
            "episodic",
            created_at=old,
            importance=0.4,
        ),
    ]
    result = consolidate(items, older_than_s=86400)
    assert result is not None and result.expert == "procedural"
