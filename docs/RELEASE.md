# Release process — Matrix Context

This repository is set up for an archival software release on GitHub with a
Zenodo DOI, plus a companion dataset on the Hugging Face Hub.

## Artifacts

| Artifact | Location |
|----------|----------|
| Software | `github.com/agent-matrix/matrix-context` (this repo) |
| Benchmark dataset | `huggingface.co/datasets/ruslanmv/moc-rag-benchmark` |
| Leaderboard Space | `huggingface.co/spaces/ruslanmv/moc-rag-leaderboard` |
| Standard contract | `moc_contract/` (schemas, `openapi.yaml`, MCP mapping, `compatibility.md`) |
| Conformance | `python -m moc_contract.conformance` → `MoC API v1 Compatible` |
| Citation metadata | `CITATION.cff`, `.zenodo.json` |

## Cutting the v0.1.0 release

1. Ensure CI is green and the working tree is clean on the default branch.
2. Confirm versions agree: `pyproject.toml`, `src/matrix_context/__init__.py`,
   `CITATION.cff`, and `.zenodo.json` all read `0.1.0`.
3. Tag and push:
   ```bash
   git tag -a v0.1.0 -m "Matrix Context 0.1.0"
   git push origin v0.1.0
   ```
4. Create the GitHub Release from the tag, pasting the `[0.1.0]` section of
   `CHANGELOG.md` as the notes.

## Zenodo DOI (GitHub integration)

1. Enable the repository in the Zenodo ↔ GitHub settings (one-time).
2. Publishing the GitHub Release above triggers Zenodo to archive the tagged
   source and mint a DOI; Zenodo reads `.zenodo.json` for metadata.
3. Add the resulting DOI badge to `README.md` and the DOI to `CITATION.cff`
   (`doi:` and `identifiers:`).

## Hugging Face (already published)

```bash
# Dataset + card + splits + result artifacts
python -m benchmarks.moc_rag_benchmark.run push-results \
  --repo ruslanmv/moc-rag-benchmark --dataset
python -m benchmarks.moc_rag_benchmark.run push-results \
  --repo ruslanmv/moc-rag-benchmark --results benchmarks/moc_rag_benchmark/results

# Leaderboard Space (Gradio)
#   benchmarks/moc_rag_benchmark/space/  ->  spaces/ruslanmv/moc-rag-leaderboard
```

Requires `huggingface_hub` and an `HF_TOKEN` with write scope. Flip the dataset
and Space to public when ready to cite.

## 0.1.0 highlights

See `CHANGELOG.md`. Engine (router, hybrid retrieval, budgeted pack assembler,
`inspect`), SQLite store, SDK + CLI, eval harness with a measured real-embedder
routing win, the `experiments/` bake-off, a minimal v1 REST surface, the
agent-generator and HomePilot adapters, and the MoC-RAG Benchmark with its
paraphrased/adversarial robustness suite.
