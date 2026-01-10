"""Context deduplication for removing semantically similar chunks.

This module provides utilities for removing duplicate or near-duplicate
chunks from retrieved results before sending to the LLM.
"""
from typing import Any
import numpy as np

from src.utils import logger, get_embedder, cosine_similarity


def deduplicate_chunks(
    chunks: list[dict[str, Any]],
    similarity_threshold: float = 0.90,
    embedding_model: str | None = None,
) -> list[dict[str, Any]]:
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

    embedder = get_embedder(embedding_model)

    texts = [chunk.get('document', '') for chunk in chunks]
    embeddings = embedder.embed_documents(texts)
    embeddings_np = np.array(embeddings)

    keep_indices = []

    for i, chunk in enumerate(chunks):
        is_duplicate = False

        for kept_idx in keep_indices:
            similarity = cosine_similarity(embeddings_np[i], embeddings_np[kept_idx])

            if similarity >= similarity_threshold:
                is_duplicate = True
                logger.debug(f"Chunk {i} is duplicate of chunk {kept_idx} (similarity: {similarity:.3f})")
                break

        if not is_duplicate:
            keep_indices.append(i)

    deduplicated = [chunks[i] for i in keep_indices]

    removed_count = len(chunks) - len(deduplicated)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate chunks ({len(deduplicated)} remaining)")

    return deduplicated


def deduplicate_by_content_hash(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    chunks: list[dict[str, Any]],
    similarity_threshold: float = 0.90,
    embedding_model: str | None = None,
    use_hash_first: bool = True,
) -> list[dict[str, Any]]:
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

    if use_hash_first:
        result = deduplicate_by_content_hash(result)

    if len(result) > 1:
        result = deduplicate_chunks(
            result,
            similarity_threshold=similarity_threshold,
            embedding_model=embedding_model,
        )

    return result

