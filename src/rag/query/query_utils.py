"""Wine terminology for query normalization and expansion.

Loads wine terminology data from JSON files in the data/ directory.
"""
import json
from pathlib import Path
from typing import Dict, List




def normalize_query(query: str) -> str:
    """
    Normalize wine terminology in query.

    Performs:
    - Lowercase conversion
    - Misspelling correction
    - Synonym replacement with canonical terminology
    - Region name normalization

    Args:
        query: Raw user query

    Returns:
        Normalized query string
    """
    query_lower = query.lower()

    # Fix misspellings first
    for misspelled, correct in MISSPELLINGS.items():
        if misspelled in query_lower:
            query_lower = query_lower.replace(misspelled, correct)

    # Replace grape synonyms with canonical terminology
    for canonical, synonyms in GRAPE_SYNONYMS.items():
        # Skip if canonical term is already in the query
        if canonical in query_lower:
            continue

        # Sort synonyms by length (longest first) to avoid partial replacements
        for syn in sorted(synonyms, key=len, reverse=True):
            # Ensure we match whole words/phrases
            padded_query = f" {query_lower} "
            padded_syn = f" {syn} "
            if padded_syn in padded_query:
                query_lower = padded_query.replace(padded_syn, f" {canonical} ").strip()
                break  # Only replace once per canonical term

    # Replace region variations with canonical terminology
    for canonical, variations in REGION_VARIATIONS.items():
        # Skip if canonical term is already in the query
        if canonical in query_lower:
            continue

        for var in sorted(variations, key=len, reverse=True):
            padded_query = f" {query_lower} "
            padded_var = f" {var} "
            if padded_var in padded_query:
                query_lower = padded_query.replace(padded_var, f" {canonical} ").strip()
                break

    return query_lower


def expand_query(query: str) -> str:
    """
    Add related wine terminology to query for better retrieval coverage.

    Args:
        query: Normalized query string

    Returns:
        Query expanded with related terminology
    """
    query_lower = query.lower()

    for key, expansion in QUERY_EXPANSIONS.items():
        if key in query_lower:
            # Add expansion terminology that aren't already in query
            expansion_terms = expansion.split()
            new_terms = [t for t in expansion_terms if t not in query_lower]
            if new_terms:
                return f"{query} {' '.join(new_terms)}"

    return query


def get_canonical_grape(term: str) -> str | None:
    """
    Get canonical grape name from a synonym or variation.

    Args:
        term: Grape name or synonym

    Returns:
        Canonical grape name or None if not found
    """
    term_lower = term.lower().strip()

    # Check if it's already canonical
    if term_lower in GRAPE_SYNONYMS:
        return term_lower

    # Search in synonyms
    for canonical, synonyms in GRAPE_SYNONYMS.items():
        if term_lower in [s.lower() for s in synonyms]:
            return canonical

    return None


def get_canonical_region(term: str) -> str | None:
    """
    Get canonical region name from a variation.

    Args:
        term: Region name or variation

    Returns:
        Canonical region name or None if not found
    """
    term_lower = term.lower().strip()

    # Check if it's already canonical
    if term_lower in REGION_VARIATIONS:
        return term_lower

    # Search in variations
    for canonical, variations in REGION_VARIATIONS.items():
        if term_lower in [v.lower() for v in variations]:
            return canonical

    return None

