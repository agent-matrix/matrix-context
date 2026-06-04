# Bake-off — embedder=st store=memory generator=none budget=90

| algorithm | recall | distractors | tokens | latency_ms | accuracy |
|---|---|---|---|---|---|
| simple_rag | 100% | 42 | 603 | 14.57 | - |
| bm25_rag | 100% | 42 | 617 | 0.18 | - |
| hybrid_rag | 100% | 41 | 608 | 11.1 | - |
| moc_rag | 100% | 38 | 563 | 23.99 | - |

**Winner:** `moc_rag`

_accuracy is shown only when a generator is configured (offline runs leave it blank and rank on recall/distractors/tokens)._