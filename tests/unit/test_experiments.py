"""Smoke test: the offline bake-off runs and ranks all four algorithms."""
from experiments.runner import run


def test_offline_bakeoff_runs():
    report = run("hashing", "memory", "none", budget=90)
    names = {r["algorithm"] for r in report["results"]}
    assert names == {"simple_rag", "bm25_rag", "hybrid_rag", "moc_rag"}
    assert report["winner"] in names
    for r in report["results"]:
        assert 0.0 <= r["recall"] <= 1.0 and r["tokens"] > 0
