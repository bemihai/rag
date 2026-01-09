"""BM25 keyword search for hybrid retrieval."""
from typing import Any
from pathlib import Path
import pickle

from rank_bm25 import BM25Okapi

from src.utils import logger


class BM25Index:
    """
    BM25 index for keyword-based retrieval.

    Provides sparse retrieval using BM25 algorithm to complement
    dense vector search. Useful for exact keyword matching.

    Args:
        index_path: Optional path to save/load index from disk.
    """

    def __init__(self, index_path: str | Path | None = None):
        self.index: BM25Okapi | None = None
        self.documents: list[dict[str, Any]] = []
        self.index_path = Path(index_path) if index_path else None

        if self.index_path and self.index_path.exists():
            self.load()

    def build_index(self, documents: list[dict[str, Any]]) -> None:
        """
        Build BM25 index from documents.

        Args:
            documents: List of document dicts with 'id', 'document', and 'metadata' keys.
        """
        if not documents:
            logger.warning("No documents provided to build BM25 index")
            return

        self.documents = documents
        tokenized_docs = [self._tokenize(doc.get('document', '')) for doc in documents]
        self.index = BM25Okapi(tokenized_docs)
        logger.info(f"Built BM25 index with {len(documents)} documents")

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization - lowercase and split on whitespace."""
        return text.lower().split()

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """
        Search using BM25.

        Args:
            query: Search query string.
            top_k: Number of top results to return.

        Returns:
            List of document dicts with 'bm25_score' added.
        """
        if not self.index:
            logger.warning("BM25 index not built, returning empty results")
            return []

        tokenized_query = self._tokenize(query)
        scores = self.index.get_scores(tokenized_query)

        # Get top-k indices sorted by score
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc = self.documents[idx].copy()
                doc['bm25_score'] = float(scores[idx])
                results.append(doc)

        logger.debug(f"BM25 search returned {len(results)} results for query: '{query[:50]}...'")
        return results

    def save(self) -> None:
        """Save index to disk."""
        if not self.index_path:
            logger.warning("No index path specified, cannot save")
            return

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, 'wb') as f:
            pickle.dump({
                'index': self.index,
                'documents': self.documents
            }, f)
        logger.info(f"Saved BM25 index to {self.index_path}")

    def load(self) -> None:
        """Load index from disk."""
        if not self.index_path or not self.index_path.exists():
            logger.warning(f"Index path does not exist: {self.index_path}")
            return

        with open(self.index_path, 'rb') as f:
            data = pickle.load(f)
            self.index = data['index']
            self.documents = data['documents']
        logger.info(f"Loaded BM25 index with {len(self.documents)} documents from {self.index_path}")

    def __len__(self) -> int:
        """Return number of documents in index."""
        return len(self.documents)

