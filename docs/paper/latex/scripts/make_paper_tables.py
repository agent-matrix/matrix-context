"""Generate every paper table (booktabs LaTeX) from the committed benchmark JSON.

No number is typed by hand: each ``tables/*.tex`` fragment is produced from
``benchmarks/moc_rag_benchmark/results/<embedder>/{results,variants}.json`` and
the dataset's ``dataset_infos.json``. Fragments are ``tabular`` environments that
the section files wrap in ``table`` floats.

    python docs/paper/latex/scripts/make_paper_tables.py [--embedder st]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BENCH = ROOT / "benchmarks" / "moc_rag_benchmark"
RESULTS = BENCH / "results"
TBLDIR = Path(__file__).resolve().parents[1] / "tables"


def _esc(s: str) -> str:
    return str(s).replace("_", r"\_")


def _pct(v):
    return "--" if v is None else f"{v * 100:.0f}\\%"


def _num(v):
    return "--" if v is None else f"{v}"


def _f3(v):
    return "--" if v is None else f"{v:.3f}"


def _best_idx(vals, lower=False):
    """Indices of the best (max, or min if lower) non-null value — ties included."""
    nums = [(i, v) for i, v in enumerate(vals) if v is not None]
    if not nums:
        return set()
    best = min(v for _, v in nums) if lower else max(v for _, v in nums)
    return {i for i, v in nums if v == best}


def _bf(s: str, on: bool) -> str:
    return r"\textbf{" + s + "}" if on else s


def _write(name: str, lines):
    TBLDIR.mkdir(parents=True, exist_ok=True)
    (TBLDIR / name).write_text("\n".join(lines) + "\n")
    print(f"  tables/{name}")


def main_results(res):
    cols = "l rrrr rr rr"
    head = (r"Method & Recall@8 & Prec@8 & MRR & nDCG@8 & "
            r"HardDistr$\downarrow$ & Tokens$\downarrow$ & UsefulRatio$\uparrow$ & RouteAcc \\")
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule", head, r"\midrule"]
    order = res["order"]
    R = res["results"]
    # Best value per key column gets bolded (ties included): recall/MRR/nDCG up,
    # hard distractors down.
    b_rec = _best_idx([R[m]["recall_at_k"] for m in order])
    b_mrr = _best_idx([R[m]["mrr"] for m in order])
    b_ndcg = _best_idx([R[m]["ndcg_at_k"] for m in order])
    b_hd = _best_idx([R[m]["hard_distractors"] for m in order], lower=True)
    for i, m in enumerate(order):
        d = R[m]
        row = (f"{_esc(m)} & {_bf(_pct(d['recall_at_k']), i in b_rec)} & "
               f"{_pct(d['precision_at_k'])} & {_bf(_f3(d['mrr']), i in b_mrr)} & "
               f"{_bf(_f3(d['ndcg_at_k']), i in b_ndcg)} & "
               f"{_bf(_num(d['hard_distractors']), i in b_hd)} & "
               f"{_num(d['tokens'])} & {_pct(d['useful_context_ratio'])} & "
               f"{_pct(d.get('routing_accuracy'))} \\\\")
        if m.startswith("moc_rag"):
            row = r"\rowcolor{mocblue!8} " + row
        lines.append(row)
    lines += [r"\bottomrule", r"\end{tabular}"]
    _write("main_results.tex", lines)


def robustness_results(var):
    cats = var["categories"]
    head = ("Method & " + " & ".join(f"R@8 {c[:3]}." for c in cats) + " & "
            + " & ".join(f"HD {c[:3]}." for c in cats)
            + r" & $\Delta$ kw$\to$adv \\")
    lines = [r"\begin{tabular}{l rrr rrr r}", r"\toprule", head, r"\midrule"]
    order = var["order"]
    Rr = var["results"]
    # Bold best per column: highest recall and lowest hard distractors per split,
    # and the smallest keyword->adversarial drop (Delta closest to zero).
    b_rec = {c: _best_idx([Rr[m][c]["recall_at_k"] for m in order]) for c in cats}
    b_hd = {c: _best_idx([Rr[m][c]["hard_distractors"] for m in order], lower=True)
            for c in cats}
    deltas = [(Rr[m][cats[-1]]["recall_at_k"] - Rr[m][cats[0]]["recall_at_k"]) * 100
              for m in order]
    b_delta = _best_idx(deltas)
    for i, m in enumerate(order):
        r = Rr[m]
        rec = " & ".join(_bf(_pct(r[c]["recall_at_k"]), i in b_rec[c]) for c in cats)
        hd = " & ".join(_bf(_num(r[c]["hard_distractors"]), i in b_hd[c]) for c in cats)
        row = f"{_esc(m)} & {rec} & {hd} & {_bf(f'{deltas[i]:+.0f}', i in b_delta)} \\\\"
        if m.startswith("moc_rag"):
            row = r"\rowcolor{mocblue!8} " + row
        lines.append(row)
    lines += [r"\bottomrule", r"\end{tabular}"]
    _write("robustness_results.tex", lines)


def ablations(var):
    """top_experts = 1 / 2 / 3 / all across query types + routing accuracy."""
    cats = var["categories"]
    moc = [m for m in var["order"] if m.startswith("moc_rag")]
    head = ("Variant & " + " & ".join(f"R@8 {c[:3]}." for c in cats)
            + r" & HD adv. & RouteAcc \\")
    lines = [r"\begin{tabular}{l rrr r r}", r"\toprule", head, r"\midrule"]
    label = {"moc_rag_e1": r"$k{=}1$", "moc_rag_e2": r"$k{=}2$",
             "moc_rag_e3": r"$k{=}3$", "moc_rag_all": "all"}
    for m in moc:
        r = var["results"][m]
        rec = " & ".join(_pct(r[c]["recall_at_k"]) for c in cats)
        lines.append(f"{label.get(m, _esc(m))} & {rec} & "
                     f"{_num(r[cats[-1]]['hard_distractors'])} & "
                     f"{_pct(r[cats[-1]].get('routing_accuracy'))} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    _write("ablations.tex", lines)


def dataset_stats():
    infos = json.loads((BENCH / "data" / "dataset_infos.json").read_text())
    c = infos.get("counts", {})
    rows = [
        ("Context items", c.get("contexts")),
        ("Queries", c.get("queries")),
        ("Context experts", c.get("experts")),
        ("Context types", c.get("types")),
        ("Domains", c.get("domains")),
        ("Query variants", c.get("variants")),
        ("Hard-negative kinds", c.get("hard_negatives")),
        ("Train / Val / Test queries",
         f"{c.get('train')} / {c.get('validation')} / {c.get('test')}"),
        ("Adversarial test queries", c.get("test_adversarial")),
    ]
    lines = [r"\begin{tabular}{l r}", r"\toprule",
             r"Statistic & Value \\", r"\midrule"]
    for k, v in rows:
        lines.append(f"{_esc(k)} & {_num(v)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    _write("dataset_stats.tex", lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--embedder", default="st")
    args = p.parse_args(argv)
    res = json.loads((RESULTS / args.embedder / "results.json").read_text())
    var = json.loads((RESULTS / args.embedder / "variants.json").read_text())
    print(f"Generating tables from results/{args.embedder}/ ->")
    main_results(res)
    robustness_results(var)
    ablations(var)
    dataset_stats()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
