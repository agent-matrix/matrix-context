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


def _write(name: str, lines):
    TBLDIR.mkdir(parents=True, exist_ok=True)
    (TBLDIR / name).write_text("\n".join(lines) + "\n")
    print(f"  tables/{name}")


def main_results(res):
    cols = "l rrrr rr rr"
    head = (r"Method & Recall@8 & Prec@8 & MRR & nDCG@8 & "
            r"HardDistr$\downarrow$ & Tokens$\downarrow$ & UsefulRatio$\uparrow$ & RouteAcc \\")
    lines = [r"\begin{tabular}{" + cols + "}", r"\toprule", head, r"\midrule"]
    for m in res["order"]:
        d = res["results"][m]
        row = (f"{_esc(m)} & {_pct(d['recall_at_k'])} & {_pct(d['precision_at_k'])} & "
               f"{_f3(d['mrr'])} & {_f3(d['ndcg_at_k'])} & {_num(d['hard_distractors'])} & "
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
    for m in var["order"]:
        r = var["results"][m]
        rec = " & ".join(_pct(r[c]["recall_at_k"]) for c in cats)
        hd = " & ".join(_num(r[c]["hard_distractors"]) for c in cats)
        delta = (r[cats[-1]]["recall_at_k"] - r[cats[0]]["recall_at_k"]) * 100
        row = f"{_esc(m)} & {rec} & {hd} & {delta:+.0f} \\\\"
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
