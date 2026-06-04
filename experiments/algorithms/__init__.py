from .simple_rag import SimpleRAG
from .bm25_rag import BM25RAG
from .hybrid_rag import HybridRAG
from .moc_rag import MoCRAG

ALGORITHMS = {a.name: a for a in (SimpleRAG, BM25RAG, HybridRAG, MoCRAG)}
__all__ = ["ALGORITHMS", "SimpleRAG", "BM25RAG", "HybridRAG", "MoCRAG"]
