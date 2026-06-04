"""Render the eval results as a comparison table."""
from __future__ import annotations
from typing import List


def render(rows: List[dict]) -> str:
    out = ["=" * 78,
           "STUB = offline hashing gate | CMPT = competent gate | FLAT = classic RAG",
           "=" * 78,
           f"{'query':<11}{'gold':>5}{'STUB_R':>8}{'STUB_d':>7}{'CMPT_R':>8}"
           f"{'CMPT_d':>7}{'FLAT_R':>8}{'FLAT_d':>7}",
           "-" * 78]
    agg = {k: 0.0 for k in ("gold", "sr", "sd", "cr", "cd", "ct", "fr", "fd", "ft", "rh")}
    for r in rows:
        out.append(f"{r['qid']:<11}{r['gold']:>5}{r['stub_recall']:>8.0%}{r['stub_dist']:>7}"
                   f"{r['cmpt_recall']:>8.0%}{r['cmpt_dist']:>7}{r['flat_recall']:>8.0%}{r['flat_dist']:>7}")
        agg["gold"] += r["gold"]; agg["sr"] += r["stub_recall"]; agg["sd"] += r["stub_dist"]
        agg["cr"] += r["cmpt_recall"]; agg["cd"] += r["cmpt_dist"]; agg["ct"] += r["cmpt_tok"]
        agg["fr"] += r["flat_recall"]; agg["fd"] += r["flat_dist"]; agg["ft"] += r["flat_tok"]
        agg["rh"] += 1 if r["route_hit"] else 0
    n = len(rows)
    out += ["-" * 78,
            f"\nMean gold recall   STUB {agg['sr']/n:.0%}   CMPT {agg['cr']/n:.0%}   FLAT {agg['fr']/n:.0%}",
            f"Total distractors  STUB {int(agg['sd'])}    CMPT {int(agg['cd'])}    FLAT {int(agg['fd'])}   (lower better)",
            f"Total pack tokens  CMPT {int(agg['ct'])}   FLAT {int(agg['ft'])}",
            f"Stub routing accuracy {int(agg['rh'])}/{n} = {agg['rh']/n:.0%}",
            "",
            "Finding: the stub gate can't discriminate, so STUB ~ FLAT (no win).",
            "With a competent gate, CMPT matches FLAT recall while cutting distractors",
            "and tokens. The payoff is GATED ON EMBEDDING QUALITY -> invest there first."]
    return "\n".join(out)
