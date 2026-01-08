"""Context deduplication for removing semantically similar chunks.

This module provides utilities for removing duplicate or near-duplicate
chunks from retrieved results before sending to the LLM. All processing
is done locally using embedding similarity - no LLM calls required.
"""
from typing import List, Dict, Any
import numpy as np

from langchain_huggingface import HuggingFaceEmbeddings

from src.utils import logger





def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector.
        vec2: Second vector.

    Returns:
        Cosine similarity score between -1 and 1.
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


def deduplicate_chunks(
    chunks: List[Dict[str, Any]],
    similarity_threshold: float = 0.90,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> List[Dict[str, Any]]:
    """
    Remove semantically duplicate chunks from a list.

    Uses embedding similarity to identify and remove near-duplicate chunks.
    Keeps the first occurrence (highest ranked) and removes subsequent
    similar chunks.

    Args:
        chunks: List of chunk dictionaries with 'document' key containing text.
        similarity_threshold: Minimum similarity to consider as duplicate (0.0-1.0).
            Default 0.90 means chunks with >90% similarity are considered duplicates.
        embedding_model: HuggingFace model name for computing embeddings.

    Returns:
        Deduplicated list of chunks, preserving original order.
    """
    if len(chunks) <= 1:
        return chunks

    embedder = _get_embedder(embedding_model)

    # Extract texts and compute embeddings
    texts = [chunk.get('document', '') for chunk in chunks]
    embeddings = embedder.embed_documents(texts)
    embeddings_np = np.array(embeddings)

    # Track which indices to keep
    keep_indices = []

    for i, chunk in enumerate(chunks):
        is_duplicate = False

        # Check against all previously kept chunks
        for kept_idx in keep_indices:
            similarity = cosine_similarity(embeddings_np[i], embeddings_np[kept_idx])

            if similarity >= similarity_threshold:
                is_duplicate = True
                logger.debug(
                    f"Chunk {i} is duplicate of chunk {kept_idx} "
                    f"(similarity: {similarity:.3f})"
                )
                break

        if not is_duplicate:
            keep_indices.append(i)

    deduplicated = [chunks[i] for i in keep_indices]

    removed_count = len(chunks) - len(deduplicated)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate chunks ({len(deduplicated)} remaining)")

    return deduplicated


def deduplicate_by_content_hash(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove exact duplicate chunks based on content hash.

    This is a fast, exact deduplication method that uses content hashes
    stored in chunk metadata. Use this before semantic deduplication
    for efficiency.

    Args:
        chunks: List of chunk dictionaries with 'metadata' containing 'content_hash'.

    Returns:
        Deduplicated list of chunks with exact duplicates removed.
    """
    seen_hashes = set()
    deduplicated = []

    for chunk in chunks:
        content_hash = chunk.get('metadata', {}).get('content_hash', '')

        if not content_hash:
            # No hash available, keep the chunk
            deduplicated.append(chunk)
            continue

        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            deduplicated.append(chunk)

    removed_count = len(chunks) - len(deduplicated)
    if removed_count > 0:
        logger.debug(f"Removed {removed_count} exact duplicate chunks by hash")

    return deduplicated


def deduplicate_context(
    chunks: List[Dict[str, Any]],
    similarity_threshold: float = 0.90,
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    use_hash_first: bool = True,
) -> List[Dict[str, Any]]:
    """
    Full deduplication pipeline for retrieved chunks.

    Combines fast hash-based deduplication with semantic deduplication
    for comprehensive duplicate removal.

    Args:
        chunks: List of chunk dictionaries.
        similarity_threshold: Threshold for semantic similarity deduplication.
        embedding_model: Model for computing semantic similarity.
        use_hash_first: If True, run hash-based dedup first for efficiency.

    Returns:
        Deduplicated list of chunks.
    """
    if not chunks:
        return chunks

    result = chunks

    # First pass: exact hash deduplication (fast)
    if use_hash_first:
        result = deduplicate_by_content_hash(result)

    # Second pass: semantic deduplication (more thorough)
    if len(result) > 1:
        result = deduplicate_chunks(
            result,
            similarity_threshold=similarity_threshold,
            embedding_model=embedding_model,
        )

    return result

