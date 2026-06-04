# MoC-RAG manuscript (LaTeX)

An arXiv/Zenodo-ready LaTeX package for *Matrix Context: Mixture-of-Contexts RAG
for Robust and Inspectable Agent Memory*. **Every figure and table is generated
from the committed benchmark result JSON** — nothing is drawn or typed by hand.

## Build

```bash
cd docs/paper/latex
make figures     # figures/*.{pdf,svg} from benchmarks/.../results/<embedder>/
make tables      # tables/*.tex from the same JSON
make paper       # build/matrix_context_moc_rag.pdf
make all         # artifacts + paper
make clean
```

Requirements: Python with `matplotlib` (artifacts) and a LaTeX toolchain
(`latexmk` + `pdflatex`, or plain `pdflatex`+`bibtex`). Select the source run
with `make all EMBEDDER=st` (default) or `EMBEDDER=hashing`.

## Layout

```
main.tex            document + author/affiliation, \input's sections
sections/           01_abstract … 10_conclusion (+ reproducibility, limitations)
figures/            generated PDF (LaTeX) and SVG (web/README) plots
tables/             generated booktabs .tex fragments
references.bib      bibliography
scripts/            make_paper_figures.py, make_paper_tables.py
build/              compiled PDF (matrix_context_moc_rag.pdf)
```

## Regenerating after new results

Re-run the benchmark, then rebuild artifacts and the paper:

```bash
python -m benchmarks.moc_rag_benchmark.run compare --embedder st --groundedness
make -C docs/paper/latex all
```

## Claim discipline

The manuscript is deliberately careful: BM25 remains strong on keyword-aligned
queries; MoC-RAG's contribution is **robustness and context efficiency under
typed, paraphrased, and adversarial conditions**, not universal supremacy over
all RAG.
