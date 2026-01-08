"""Hybrid retriever combining vector and keyword search."""
from typing import List, Dict, Any

from src.rag.retriever import ChromaRetriever
from src.rag.retriever.keyword_search import BM25Index
from src.utils import logger


class HybridRetriever:
    """
    Combine vector similarity and BM25 keyword search using Reciprocal Rank Fusion.

    This retriever performs both dense (vector) and sparse (BM25) retrieval,
    then fuses the results using RRF to get the best of both approaches.

    Args:
        vector_retriever: ChromaRetriever instance for vector search.
        bm25_index: BM25Index instance for keyword search.
        vector_weight: Weight for vector search results (default: 0.7).
        keyword_weight: Weight for BM25 results (default: 0.3).
    """

    def __init__(
        self,
        vector_retriever: ChromaRetriever,
        bm25_index: BM25Index,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        self.vector_retriever = vector_retriever
        self.bm25_index = bm25_index
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

        logger.info(
            f"Initialized HybridRetriever with weights: "
            f"vector={vector_weight}, keyword={keyword_weight}"
        )

    def retrieve(
        self,
        query: str,
        n_results: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve using hybrid search with Reciprocal Rank Fusion.

        Args:
            query: User's query string.
            n_results: Number of final results to return.
            **kwargs: Additional arguments passed to vector retriever (e.g., where filters).

        Returns:
            List of document dicts with 'rrf_score' added, sorted by relevance.
        """
        # Retrieve more candidates from each source for better fusion
        candidates_per_source = n_results * 2

        # Get vector results
        vector_results = self.vector_retriever.retrieve(
            query,
            n_results=candidates_per_source,
            **kwargs
        )

        # Get BM25 results
        bm25_results = self.bm25_index.search(query, top_k=candidates_per_source)

        # Fuse results using RRF
        fused = self._reciprocal_rank_fusion(vector_results, bm25_results)

        logger.info(
            f"Hybrid retrieval: {len(vector_results)} vector + {len(bm25_results)} BM25 "
            f"-> {min(len(fused), n_results)} fused results"
        )

        return fused[:n_results]

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine rankings using Reciprocal Rank Fusion (RRF).

        RRF score = sum(weight / (k + rank)) for each ranking list.

        Args:
            vector_results: Results from vector search.
            bm25_results: Results from BM25 search.
            k: RRF constant (default: 60, as per original RRF paper).

        Returns:
            Fused and sorted list of documents.
        """
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        # Score vector results
        for rank, doc in enumerate(vector_results):
            doc_id = doc['id']
            scores[doc_id] = scores.get(doc_id, 0) + self.vector_weight / (k + rank + 1)
            doc_map[doc_id] = doc

        # Score BM25 results
        for rank, doc in enumerate(bm25_results):
            doc_id = doc['id']
            scores[doc_id] = scores.get(doc_id, 0) + self.keyword_weight / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids:
            doc = doc_map[doc_id].copy()
            doc['rrf_score'] = scores[doc_id]
            results.append(doc)

        return results

