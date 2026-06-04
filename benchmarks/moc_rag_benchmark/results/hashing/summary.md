# MoC-RAG Benchmark — test split

embedder=`hashing` · K=8 · budget=200 tokens · queries=120 · contexts=1000

| Method | Recall@K | Prec@K | MRR | nDCG@K | HardDistr ↓ | Distr ↓ | Tokens ↓ | UsefulRatio ↑ | CtxEff ↑ | RouteAcc | Lat(ms) | Ground |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25_rag | 78% | 19% | 0.719 | 0.727 | 167 | 1566 | 23560 | 12% | 3.969 | - | 7.84 | 83% |
| dense_rag | 80% | 20% | 0.701 | 0.719 | 109 | 1529 | 23548 | 12% | 4.077 | - | 2.05 | 88% |
| hybrid_rag | 79% | 20% | 0.734 | 0.732 | 142 | 1566 | 23612 | 12% | 4.002 | - | 10.02 | 88% |
| metadata_rag | 82% | 20% | 0.728 | 0.742 | 169 | 1514 | 23362 | 12% | 4.195 | - | 1.80 | 90% |
| reranked_rag | 85% | 21% | 0.776 | 0.785 | 123 | 1512 | 23515 | 13% | 4.338 | - | 1.78 | 90% |
| moc_rag_e1 | 72% | 18% | 0.673 | 0.675 | 68 | 1520 | 23544 | 11% | 3.674 | 78% | 2.58 | 73% |
| moc_rag_e2 | 78% | 19% | 0.727 | 0.724 | 87 | 1528 | 23567 | 12% | 3.946 | 90% | 4.12 | 85% |
| moc_rag_e3 | 82% | 20% | 0.772 | 0.767 | 101 | 1517 | 23591 | 12% | 4.154 | 97% | 5.73 | 88% |
| moc_rag_all | 82% | 21% | 0.793 | 0.782 | 100 | 1535 | 23601 | 13% | 4.195 | 100% | 10.35 | 89% |

**Winner:** `reranked_rag`

_Ranked by answer correctness when measured, else Recall@K, then fewest hard distractors, then fewest tokens. ↓ lower is better, ↑ higher is better._