"""Retriever component for querying ChromaDB collections."""
from typing import List, Dict, Any

import chromadb as cdb
from langchain_huggingface import HuggingFaceEmbeddings

from src.utils import logger, initialize_chroma_client


class ChromaRetriever:
    """
    Retriever class for querying ChromaDB collections and retrieving relevant documents.

    Args:
        client: ChromaDB client instance.
        collection_name: Name of the collection to query.
        embedding_model: HuggingFace agents name for embeddings.
        n_results: Number of results to retrieve (default: 5).
        similarity_threshold: Optional minimum similarity score to filter results (default: None).
    """

    def __init__(
        self,
        client: cdb.ClientAPI,
        collection_name: str,
        embedding_model: str,
        n_results: int = 5,
        similarity_threshold: float | None = None,
    ):
        self.client = client
        self.collection_name = collection_name
        self.n_results = n_results
        self.similarity_threshold = similarity_threshold
        self.embedder = HuggingFaceEmbeddings(model_name=embedding_model)

        try:
            self.collection = client.get_collection(collection_name)
            logger.info(f"Retrieved collection '{collection_name}' for querying")
        except Exception as e:
            logger.error(f"Failed to get collection '{collection_name}': {e}")
            raise

    def retrieve(self, query: str, n_results: int | None = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a given query.

        Args:
            query: The user's query string.
            n_results: Optional override for number of results (uses instance default if None).

        Returns:
            List of dictionaries containing retrieved documents with metadata and scores.
            Each dict has keys: 'id', 'document', 'metadata', 'distance', 'similarity'.
        """
        if n_results is None:
            n_results = self.n_results

        try:
            query_embedding = self.embedder.embed_query(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            retrieved_docs = []

            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    doc_id = results['ids'][0][i]
                    document = results['documents'][0][i]
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else None

                    # Convert distance to similarity score (for cosine distance: similarity = 1 - distance)
                    similarity = 1 - distance if distance is not None else None

                    # Apply similarity threshold filter if set
                    if self.similarity_threshold is not None and similarity is not None:
                        if similarity < self.similarity_threshold:
                            continue

                    retrieved_docs.append({
                        'id': doc_id,
                        'document': document,
                        'metadata': metadata,
                        'distance': distance,
                        'similarity': similarity,
                    })

                logger.info(f"Retrieved {len(retrieved_docs)} documents for query: '{query[:50]}...'")
            else:
                logger.warning(f"No results found for query: '{query[:50]}...'")

            return retrieved_docs

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []

    def retrieve_with_filter(
        self,
        query: str,
        where: Dict[str, Any] | None = None,
        where_document: Dict[str, Any] | None = None,
        n_results: int | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents with metadata filtering.

        Args:
            query: The user's query string.
            where: Optional metadata filter (e.g., {"source": "specific_book.pdf"}).
            where_document: Optional document content filter.
            n_results: Optional override for number of results.

        Returns:
            List of dictionaries containing retrieved documents with metadata and scores.
        """
        if n_results is None:
            n_results = self.n_results

        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_query(query)

            # Build query parameters
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"]
            }

            if where is not None:
                query_params["where"] = where
            if where_document is not None:
                query_params["where_document"] = where_document

            # Query the collection
            results = self.collection.query(**query_params)

            # Format results (same as retrieve method)
            retrieved_docs = []

            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    doc_id = results['ids'][0][i]
                    document = results['documents'][0][i]
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else None

                    similarity = 1 - distance if distance is not None else None

                    if self.similarity_threshold is not None and similarity is not None:
                        if similarity < self.similarity_threshold:
                            continue

                    retrieved_docs.append({
                        'id': doc_id,
                        'document': document,
                        'metadata': metadata,
                        'distance': distance,
                        'similarity': similarity,
                    })

                logger.info(f"Retrieved {len(retrieved_docs)} filtered documents")
            else:
                logger.warning("No results found with applied filters")

            return retrieved_docs

        except Exception as e:
            logger.error(f"Error during filtered retrieval: {e}")
            return []

