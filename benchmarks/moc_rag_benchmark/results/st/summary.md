# MoC-RAG Benchmark — test split

embedder=`st` · K=8 · budget=200 tokens · queries=120 · contexts=1000

| Method | Recall@K | Prec@K | MRR | nDCG@K | HardDistr ↓ | Distr ↓ | Tokens ↓ | UsefulRatio ↑ | CtxEff ↑ | RouteAcc | Lat(ms) | Ground |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25_rag | 78% | 19% | 0.719 | 0.727 | 167 | 1566 | 23560 | 12% | 3.969 | - | 7.47 | 83% |
| dense_rag | 78% | 19% | 0.558 | 0.617 | 271 | 1486 | 23539 | 12% | 3.972 | - | 12.01 | 83% |
| hybrid_rag | 82% | 21% | 0.723 | 0.740 | 244 | 1550 | 23519 | 12% | 4.209 | - | 20.23 | 84% |
| metadata_rag | 82% | 20% | 0.703 | 0.721 | 273 | 1486 | 23364 | 13% | 4.194 | - | 12.07 | 84% |
| reranked_rag | 82% | 21% | 0.717 | 0.745 | 249 | 1516 | 23499 | 12% | 4.213 | - | 12.53 | 86% |
| moc_rag_e1 | 81% | 20% | 0.748 | 0.760 | 104 | 1520 | 23509 | 12% | 4.147 | 84% | 12.26 | 77% |
| moc_rag_e2 | 85% | 21% | 0.768 | 0.781 | 122 | 1536 | 23547 | 13% | 4.332 | 95% | 13.35 | 86% |
| moc_rag_e3 | 86% | 22% | 0.789 | 0.796 | 156 | 1527 | 23529 | 13% | 4.399 | 99% | 15.14 | 89% |
| moc_rag_all | 85% | 21% | 0.766 | 0.779 | 196 | 1560 | 23568 | 12% | 4.307 | 100% | 20.62 | 89% |

**Winner:** `moc_rag_e3`

_Ranked by answer correctness when measured, else Recall@K, then fewest hard distractors, then fewest tokens. ↓ lower is better, ↑ higher is better._