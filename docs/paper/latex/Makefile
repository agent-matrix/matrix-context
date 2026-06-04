# MoC-RAG manuscript build.
#
#   make figures   regenerate figures/*.{pdf,svg} from committed benchmark JSON
#   make tables    regenerate tables/*.tex from committed benchmark JSON
#   make paper     compile main.tex -> build/matrix_context_moc_rag.pdf
#   make all       artifacts + paper
#   make clean     remove LaTeX aux + build/
#
# Requires: python (matplotlib) for artifacts; a LaTeX toolchain
# (latexmk + pdflatex, or pdflatex/bibtex) for the PDF.

PYTHON   ?= python
EMBEDDER ?= st
SCRIPTS   = scripts
BUILD     = build
PDFNAME   = matrix_context_moc_rag

# Run scripts from the repo root so their relative result paths resolve.
REPO_ROOT = ../../..

.PHONY: all artifacts figures tables paper clean

all: artifacts paper

artifacts: figures tables

figures:
	cd $(REPO_ROOT) && $(PYTHON) docs/paper/latex/$(SCRIPTS)/make_paper_figures.py --embedder $(EMBEDDER)

tables:
	cd $(REPO_ROOT) && $(PYTHON) docs/paper/latex/$(SCRIPTS)/make_paper_tables.py --embedder $(EMBEDDER)

paper: $(BUILD)/$(PDFNAME).pdf

$(BUILD)/$(PDFNAME).pdf: main.tex references.bib sections/*.tex figures/*.pdf tables/*.tex
	mkdir -p $(BUILD)
	@if command -v latexmk >/dev/null 2>&1; then \
	  latexmk -pdf -interaction=nonstopmode -halt-on-error \
	    -output-directory=$(BUILD) -jobname=$(PDFNAME) main.tex ; \
	else \
	  pdflatex -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) -jobname=$(PDFNAME) main.tex ; \
	  ( cd $(BUILD) && bibtex $(PDFNAME) ) || true ; \
	  pdflatex -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) -jobname=$(PDFNAME) main.tex ; \
	  pdflatex -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) -jobname=$(PDFNAME) main.tex ; \
	fi
	@echo "built $(BUILD)/$(PDFNAME).pdf"

clean:
	rm -rf $(BUILD)
	rm -f *.aux *.log *.out *.bbl *.blg *.fls *.fdb_latexmk *.toc
