"""The framework-integration demos work: ingest a document and recall from it.

The core (download cached → ingest → recall) runs offline in CI. The
framework-specific checks skip unless the framework is installed.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

INTEG = Path(__file__).resolve().parents[2] / "tutorials" / "integrations"


def _load(name):
    if str(INTEG) not in sys.path:
        sys.path.insert(0, str(INTEG))
    spec = importlib.util.spec_from_file_location(name, INTEG / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_ingest_core_recalls_from_document():
    mc = _load("mc_ingest")
    ctx = mc.build_context()
    assert len(ctx.store.all_items()) >= 10
    out = mc.retrieve(ctx, "What license is PostgreSQL released under?", max_tokens=300)
    assert "License" in out


def test_langchain_retriever_returns_documents():
    pytest.importorskip("langchain_core")
    mc = _load("mc_ingest")
    lc = _load("langchain_demo")
    r = lc.MatrixContextRetriever(ctx=mc.build_context(), scope=mc.SCOPE)
    docs = r.invoke("What license is PostgreSQL released under?")
    assert docs and hasattr(docs[0], "page_content")


def test_langgraph_app_runs():
    pytest.importorskip("langgraph")
    lg = _load("langgraph_demo")
    out = lg.build_graph().invoke({"question": "What does ACID mean?"})
    assert out["answer"]
