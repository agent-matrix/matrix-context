# MoC-RAG Benchmark — robustness by query type

embedder=`hashing` · K=8 · budget=200 tokens · parallel test topics phrased as keyword, paraphrased, adversarial

Recall@K should hold across columns; a method that **drops** from `keyword` to `adversarial` is brittle to lexical noise.

| Method | R@8 keyword | R@8 paraphrased | R@8 adversarial | HardDistr keyword | HardDistr paraphrased | HardDistr adversarial | RouteAcc |
|---|---|---|---|---|---|---|---|
| bm25_rag | 100% | 81% | 64% | 27 | 68 | 72 | - |
| dense_rag | 100% | 79% | 71% | 17 | 39 | 53 | - |
| hybrid_rag | 100% | 81% | 66% | 24 | 48 | 70 | - |
| metadata_rag | 100% | 88% | 67% | 29 | 61 | 79 | - |
| reranked_rag | 100% | 90% | 73% | 20 | 44 | 59 | - |
| moc_rag_e1 | 100% | 64% | 67% | 16 | 27 | 25 | 75% |
| moc_rag_e2 | 100% | 69% | 75% | 18 | 32 | 37 | 98% |
| moc_rag_e3 | 100% | 78% | 76% | 19 | 35 | 47 | 100% |
| moc_rag_all | 100% | 84% | 72% | 19 | 33 | 48 | 100% |

## Recall drop (keyword → adversarial)

| Method | Δ Recall@K |
|---|---|
| bm25_rag | -36% |
| dense_rag | -29% |
| hybrid_rag | -34% |
| metadata_rag | -33% |
| reranked_rag | -27% |
| moc_rag_e1 | -33% |
| moc_rag_e2 | -25% |
| moc_rag_e3 | -24% |
| moc_rag_all | -28% |