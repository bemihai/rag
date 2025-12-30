"""Prompt compression for reducing context size before LLM.

This module provides utilities for compressing retrieved context to reduce
token usage. All processing is done locally - no LLM calls required.

Compression strategies:
1. Sentence-level deduplication (remove semantically similar sentences)
2. Extractive compression (keep most relevant sentences using TF-IDF)
3. Length limiting (truncate to max tokens/characters)
"""
from typing import List, Dict, Any, Tuple
import re
from collections import Counter
import math

from src.utils import logger


def _tokenize_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence splitting on common delimiters
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _compute_tfidf(sentences: List[str]) -> List[Tuple[str, float]]:
    """
    Compute TF-IDF scores for sentences.

    Args:
        sentences: List of sentences.

    Returns:
        List of (sentence, score) tuples sorted by score descending.
    """
    if not sentences:
        return []

    # Tokenize each sentence into words
    tokenized = [s.lower().split() for s in sentences]

    # Compute document frequency
    doc_freq = Counter()
    for tokens in tokenized:
        doc_freq.update(set(tokens))

    n_docs = len(sentences)

    # Compute TF-IDF for each sentence
    scored = []
    for sentence, tokens in zip(sentences, tokenized):
        if not tokens:
            scored.append((sentence, 0.0))
            continue

        # Term frequency (normalized)
        tf = Counter(tokens)
        max_tf = max(tf.values())

        # TF-IDF score
        score = 0.0
        for term, count in tf.items():
            tf_norm = count / max_tf
            idf = math.log(n_docs / (doc_freq[term] + 1))
            score += tf_norm * idf

        # Normalize by sentence length
        score /= len(tokens)
        scored.append((sentence, score))

    return sorted(scored, key=lambda x: x[1], reverse=True)


def extractive_compress(
    text: str,
    max_sentences: int = 10,
    min_sentence_length: int = 20,
) -> str:
    """
    Compress text by keeping most important sentences using TF-IDF.

    Args:
        text: Text to compress.
        max_sentences: Maximum number of sentences to keep.
        min_sentence_length: Minimum sentence length to consider.

    Returns:
        Compressed text with top sentences.
    """
    sentences = _tokenize_sentences(text)

    # Filter short sentences
    sentences = [s for s in sentences if len(s) >= min_sentence_length]

    if len(sentences) <= max_sentences:
        return text

    # Score sentences
    scored = _compute_tfidf(sentences)

    # Keep top sentences, maintaining original order
    top_sentences = set(s for s, _ in scored[:max_sentences])

    result = []
    for sentence in _tokenize_sentences(text):
        if sentence in top_sentences:
            result.append(sentence)

    compressed = ' '.join(result)

    logger.debug(
        f"Extractive compression: {len(sentences)} -> {len(result)} sentences "
        f"({len(compressed)}/{len(text)} chars)"
    )

    return compressed


def remove_redundant_sentences(
    text: str,
    similarity_threshold: float = 0.8,
) -> str:
    """
    Remove sentences that are near-duplicates of earlier sentences.

    Uses simple word overlap for efficiency (no embeddings).

    Args:
        text: Text to deduplicate.
        similarity_threshold: Jaccard similarity threshold for duplicates.

    Returns:
        Text with redundant sentences removed.
    """
    sentences = _tokenize_sentences(text)

    if len(sentences) <= 1:
        return text

    kept = []
    kept_tokens = []

    for sentence in sentences:
        tokens = set(sentence.lower().split())

        is_duplicate = False
        for prev_tokens in kept_tokens:
            # Jaccard similarity
            if not tokens or not prev_tokens:
                continue
            intersection = len(tokens & prev_tokens)
            union = len(tokens | prev_tokens)
            similarity = intersection / union if union > 0 else 0

            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(sentence)
            kept_tokens.append(tokens)

    if len(kept) < len(sentences):
        logger.debug(f"Removed {len(sentences) - len(kept)} redundant sentences")

    return ' '.join(kept)


def truncate_to_limit(
    text: str,
    max_chars: int = 8000,
    max_words: int | None = None,
) -> str:
    """
    Truncate text to character or word limit.

    Args:
        text: Text to truncate.
        max_chars: Maximum characters (default 8000 ~ 2000 tokens).
        max_words: Maximum words (optional).

    Returns:
        Truncated text ending at sentence boundary if possible.
    """
    if len(text) <= max_chars:
        if max_words is None or len(text.split()) <= max_words:
            return text

    # Try to end at sentence boundary
    sentences = _tokenize_sentences(text)
    result = []
    char_count = 0
    word_count = 0

    for sentence in sentences:
        sentence_chars = len(sentence) + 1  # +1 for space
        sentence_words = len(sentence.split())

        if char_count + sentence_chars > max_chars:
            break
        if max_words and word_count + sentence_words > max_words:
            break

        result.append(sentence)
        char_count += sentence_chars
        word_count += sentence_words

    return ' '.join(result)


def compress_context(
    context: str,
    max_chars: int = 8000,
    use_extractive: bool = True,
    remove_redundant: bool = True,
) -> str:
    """
    Full compression pipeline for RAG context.

    Applies multiple compression strategies in order:
    1. Remove redundant sentences (fast, preserves info)
    2. Extractive compression (if still too long)
    3. Truncation (as last resort)

    Args:
        context: Retrieved context to compress.
        max_chars: Maximum output length in characters.
        use_extractive: Whether to use TF-IDF extractive compression.
        remove_redundant: Whether to remove redundant sentences.

    Returns:
        Compressed context.
    """
    if not context or len(context) <= max_chars:
        return context

    result = context

    # Step 1: Remove redundant sentences
    if remove_redundant:
        result = remove_redundant_sentences(result)

    # Step 2: Extractive compression if still too long
    if use_extractive and len(result) > max_chars:
        # Estimate sentences needed
        avg_sentence_len = len(result) / max(1, len(_tokenize_sentences(result)))
        max_sentences = int(max_chars / avg_sentence_len) + 2
        result = extractive_compress(result, max_sentences=max_sentences)

    # Step 3: Hard truncate if still too long
    if len(result) > max_chars:
        result = truncate_to_limit(result, max_chars=max_chars)

    original_len = len(context)
    compressed_len = len(result)
    ratio = compressed_len / original_len if original_len > 0 else 1.0

    logger.info(
        f"Context compression: {original_len} -> {compressed_len} chars "
        f"({ratio:.1%} of original)"
    )

    return result

