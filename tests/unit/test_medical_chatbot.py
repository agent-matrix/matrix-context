"""The medical-assistant example recalls the right typed memory and flags
contraindications — the quality check that backs the tutorial demo."""
import importlib.util
from pathlib import Path

from matrix_context import ContextManager

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "examples" / "medical_chatbot.py"


def _load():
    spec = importlib.util.spec_from_file_location("medical_chatbot", EX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_quality_verification_passes():
    m = _load()
    ctx = ContextManager.create("med-test", path=":memory:")
    m.seed(ctx)
    assert m.verify(ctx) is True          # all labeled cases pass


def test_allergy_contraindication_is_flagged():
    m = _load()
    ctx = ContextManager.create("med-test2", path=":memory:")
    m.seed(ctx)
    res = m.answer(ctx, "Can I prescribe amoxicillin for the sinus infection?")
    assert res["warning"] and "CONTRAINDICATED" in res["warning"]
    # pinned safety context is always recalled
    facts = " ".join(res["facts"]).lower()
    assert "allergic to penicillin" in facts


def test_unrelated_query_still_recalls_pinned_safety_context():
    m = _load()
    ctx = ContextManager.create("med-test3", path=":memory:")
    m.seed(ctx)
    res = m.answer(ctx, "What was the patient's last HbA1c?")
    facts = " ".join(res["facts"]).lower()
    assert "7.8%" in facts
    assert "allergic to penicillin" in facts or "never prescribe" in facts  # profile/policy pinned
