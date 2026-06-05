"""Medical assistant chatbot on Matrix Context — with a quality check.

A safety-critical domain is the sharpest test of *typed, inspectable* memory: the
assistant must always recall the patient's allergies and the clinical safety
rules, and never drop them, even for an unrelated question. Matrix Context makes
that guarantee explicit:

  * patient facts  -> the `profile` expert
  * clinical rules -> the `policy` expert   (both PINNED = always injectable)
  * guidelines     -> `semantic`
  * visit history  -> `episodic`
  * drug facts     -> `document`
  * current visit  -> `session`

`build_pack(query, pin_experts=("profile","policy"))` guarantees the safety
context rides along every turn. The script answers a few turns (grounded on the
recalled pack), then runs a labeled **quality verification** and prints a score.

Run:  python examples/medical_chatbot.py        (offline; deterministic responder)
      ANTHROPIC_API_KEY=… python examples/medical_chatbot.py --llm   (real answers)
"""
from __future__ import annotations

import argparse
import sys

from matrix_context import ContextManager

PINNED = ("profile", "policy")

# A small, realistic patient memory. (content, expert, importance)
PATIENT = [
    ("Patient is allergic to penicillin (severe — anaphylaxis).", "profile", 0.98),
    ("Patient has type 2 diabetes.", "profile", 0.9),
    ("Patient is on metformin 1000 mg twice daily.", "profile", 0.85),
    ("Patient is on warfarin (anticoagulant).", "profile", 0.9),
    ("Clinical rule: never prescribe a drug the patient is allergic to.", "policy", 0.98),
    ("Clinical rule: avoid NSAIDs (e.g. ibuprofen) in patients on anticoagulants — bleeding risk.", "policy", 0.95),
    ("Policy: confirm renal function before increasing the metformin dose.", "policy", 0.8),
    ("Guideline: first-line pharmacotherapy for type 2 diabetes is metformin.", "semantic", 0.8),
    ("Decision: target HbA1c < 7% for this patient.", "semantic", 0.75),
    ("On 2026-03-10 the patient reported a rash after amoxicillin.", "episodic", 0.7),
    ("Last HbA1c on 2026-04-01 was 7.8%.", "episodic", 0.75),
    ("Amoxicillin is a penicillin-class antibiotic.", "document", 0.7),
    ("Ibuprofen is an NSAID.", "document", 0.7),
    ("Current visit: the patient complains of a sinus infection.", "session", 0.6),
]

# Demo drug knowledge for the deterministic safety check (grounded on the pack).
DRUG_CLASS = {"amoxicillin": "penicillin", "ibuprofen": "nsaid", "metformin": "biguanide"}


def seed(ctx: ContextManager) -> None:
    for content, expert, importance in PATIENT:
        ctx.remember(content, expert=expert, importance=importance, scope="patient:demo")


def recall(ctx: ContextManager, query: str, max_tokens: int = 220):
    """The typed, pinned recall used for every turn."""
    return ctx.build_pack(query, scope="patient:demo", max_tokens=max_tokens,
                          pin_experts=PINNED, top_experts=3)


def safety_warning(query: str, pack_text: str) -> str | None:
    """Deterministic, grounded contraindication check over the recalled context."""
    q = query.lower()
    text = pack_text.lower()
    for drug, cls in DRUG_CLASS.items():
        if drug in q and any(w in q for w in ("prescribe", "give", "start", "take", "can ", "should")):
            # allergy contraindication (drug class matches a stated allergy)
            if cls == "penicillin" and "allergic to penicillin" in text:
                return (f"⚠️ CONTRAINDICATED: {drug} is a {cls}-class drug and the patient "
                        f"is allergic to penicillin (anaphylaxis). Do not prescribe.")
            # interaction contraindication
            if cls == "nsaid" and "anticoagulant" in text:
                return (f"⚠️ CAUTION: {drug} is an NSAID and the patient is on an "
                        f"anticoagulant (warfarin) — bleeding risk. Avoid / seek alternative.")
    return None


def answer(ctx: ContextManager, query: str, use_llm: bool = False) -> dict:
    pack = recall(ctx, query)
    facts = [p.item.content for p in pack.items]
    pack_text = pack.to_prompt()
    warn = safety_warning(query, pack_text)

    if use_llm:
        reply = _llm(query, pack_text, warn)
    else:
        # Deterministic, grounded responder (offline): surface the recalled facts.
        lead = (warn + "\n\n") if warn else ""
        reply = lead + "Based on the patient's record:\n" + "\n".join(f"  • {f}" for f in facts[:4])
    return {"answer": reply, "warning": warn, "facts": facts,
            "selected_experts": pack.selected_experts, "tokens": pack.tokens}


def _llm(query: str, pack_text: str, warn: str | None) -> str:  # pragma: no cover - network
    import anthropic
    sys_prompt = ("You are a careful clinical assistant. Use ONLY the provided patient "
                  "context. If a request is contraindicated by an allergy or interaction, "
                  "refuse and explain. Be concise.")
    note = f"\n\nSafety check flagged: {warn}" if warn else ""
    msg = anthropic.Anthropic().messages.create(
        model="claude-sonnet-4-6", max_tokens=400,
        system=sys_prompt,
        messages=[{"role": "user", "content": f"{pack_text}{note}\n\nQuestion: {query}"}],
    )
    return msg.content[0].text


# --------------------------------------------------------------------------- #
# Quality verification — does the right typed memory get recalled every time?
# --------------------------------------------------------------------------- #
# (query, must_appear_in_pack[...], expect_safety_warning)
CASES = [
    ("Is the patient allergic to anything?", ["allergic to penicillin"], False),
    ("What medications is the patient taking?", ["metformin", "warfarin"], False),
    ("Can I prescribe amoxicillin for the sinus infection?",
     ["allergic to penicillin", "never prescribe a drug the patient is allergic"], True),
    ("Can the patient take ibuprofen for pain?",
     ["anticoagulant", "NSAID"], True),
    ("What is the first-line treatment for type 2 diabetes?", ["first-line", "metformin"], False),
    ("What was the patient's last HbA1c?", ["7.8%"], False),
]


def verify(ctx: ContextManager) -> bool:
    print("\n=== Quality verification ===")
    passed = 0
    for query, must, expect_warn in CASES:
        res = answer(ctx, query)
        pack_text = "\n".join(res["facts"]).lower()
        recalled = all(m.lower() in pack_text for m in must)
        warn_ok = (res["warning"] is not None) == expect_warn
        ok = recalled and warn_ok
        passed += ok
        flag = "PASS" if ok else "FAIL"
        bits = []
        if not recalled:
            bits.append("missing recall of " + ", ".join(repr(m) for m in must if m.lower() not in pack_text))
        if not warn_ok:
            bits.append(f"safety warning expected={expect_warn} got={res['warning'] is not None}")
        print(f"  [{flag}] {query}")
        if bits:
            print("         -> " + "; ".join(bits))
    n = len(CASES)
    print(f"\nQuality: {passed}/{n} cases passed "
          f"({'all recalls grounded + safety flags correct' if passed == n else 'see failures above'})")
    return passed == n


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Medical assistant on Matrix Context")
    p.add_argument("--llm", action="store_true", help="use Anthropic for the reply (needs ANTHROPIC_API_KEY)")
    args = p.parse_args(argv)

    ctx = ContextManager.create("medical-demo", path=":memory:")
    seed(ctx)

    print("=== Sample turns (typed recall, profile+policy pinned) ===")
    for q in ["Can I prescribe amoxicillin for the sinus infection?",
              "What is the first-line treatment for type 2 diabetes?"]:
        res = answer(ctx, q, use_llm=args.llm)
        print(f"\npatient/clinician> {q}")
        print(f"assistant> {res['answer']}")
        print(f"   (routed to: {res['selected_experts']}, {res['tokens']} tokens)")

    print("\n=== Why it recalled that (inspect) ===")
    print(ctx.inspect("Can I prescribe amoxicillin?", scope="patient:demo",
                      max_tokens=160, pin_experts=PINNED))

    ok = verify(ctx)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
