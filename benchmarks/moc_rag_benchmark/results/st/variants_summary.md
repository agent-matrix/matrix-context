# MoC-RAG Benchmark — robustness by query type

embedder=`st` · K=8 · budget=200 tokens · parallel test topics phrased as keyword, paraphrased, adversarial

Recall@K should hold across columns; a method that **drops** from `keyword` to `adversarial` is brittle to lexical noise.

| Method | R@8 keyword | R@8 paraphrased | R@8 adversarial | HardDistr keyword | HardDistr paraphrased | HardDistr adversarial | RouteAcc |
|---|---|---|---|---|---|---|---|
| bm25_rag | 100% | 81% | 64% | 27 | 68 | 72 | - |
| dense_rag | 83% | 79% | 74% | 64 | 104 | 103 | - |
| hybrid_rag | 96% | 88% | 71% | 52 | 101 | 91 | - |
| metadata_rag | 92% | 88% | 71% | 63 | 107 | 103 | - |
| reranked_rag | 83% | 86% | 78% | 56 | 96 | 97 | - |
| moc_rag_e1 | 100% | 84% | 69% | 22 | 40 | 42 | 75% |
| moc_rag_e2 | 96% | 86% | 78% | 26 | 48 | 48 | 96% |
| moc_rag_e3 | 96% | 89% | 79% | 30 | 64 | 62 | 100% |
| moc_rag_all | 98% | 85% | 77% | 34 | 82 | 80 | 100% |

## Recall drop (keyword → adversarial)

| Method | Δ Recall@K |
|---|---|
| bm25_rag | -36% |
| dense_rag | -9% |
| hybrid_rag | -25% |
| metadata_rag | -21% |
| reranked_rag | -5% |
| moc_rag_e1 | -31% |
| moc_rag_e2 | -18% |
| moc_rag_e3 | -17% |
| moc_rag_all | -21% |