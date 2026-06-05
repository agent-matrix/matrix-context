#!/usr/bin/env sh
# Build a clean, self-contained arXiv source bundle from docs/paper/latex/.
#
# Produces:
#   build/arxiv/                          source + main.bbl + figures (no aux, no PDF)
#   build/matrix_context_moc_rag_arxiv.tar.gz
#
# The bundle includes main.bbl and excludes main.pdf, so arXiv builds it with
# pdflatex alone (no bibtex pass, and it is treated as a TeX source submission,
# not a PDF-only one). This script verifies exactly that before packing.
set -eu

HERE="$(cd "$(dirname "$0")/.." && pwd)"   # docs/paper/latex
OUT="$HERE/build/arxiv"
TARBALL="$HERE/build/matrix_context_moc_rag_arxiv.tar.gz"

rm -rf "$OUT"
mkdir -p "$OUT/sections" "$OUT/tables" "$OUT/figures"
cp "$HERE/main.tex" "$HERE/references.bib" "$OUT/"
cp "$HERE/sections/"*.tex "$OUT/sections/"
cp "$HERE/tables/"*.tex "$OUT/tables/"
cp "$HERE/figures/"*.pdf "$OUT/figures/"   # PDF figures only (pdflatex path)

# Generate main.bbl (run inside the bundle so the .aux/.bbl match main.tex).
cd "$OUT"
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
bibtex main >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null

# Strip aux + the compiled PDF, keeping main.bbl.
rm -f main.aux main.log main.out main.blg main.fls main.fdb_latexmk main.pdf

# Verify the bundle builds with pdflatex ALONE (the real arXiv path). Two passes,
# no bibtex: pass 1 writes the .aux, pass 2 resolves \ref/\cite cross-references.
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
if grep -qiE "undefined|warning: citation" main.log; then
  echo "ERROR: undefined references/citations in the arXiv bundle" >&2
  exit 1
fi
echo "arXiv bundle OK (pdflatex-only): $(grep -aoE 'Output written on .*' main.log)"

# Final strip (remove what the verify pass regenerated) and pack.
rm -f main.aux main.log main.out main.blg main.fls main.fdb_latexmk main.pdf
tar -czf "$TARBALL" main.tex references.bib main.bbl sections tables figures
echo "wrote $TARBALL"
echo "contents:"
tar -tzf "$TARBALL" | sed 's/^/  /'
