"""Query analysis for metadata-based filtering.

This module analyzes user queries to extract wine entities and build
metadata filters for improved retrieval. All processing is local.
"""
from typing import Dict, List, Any
from dataclasses import dataclass, field

from src.rag.utils.metadata_extractor import (
    extract_grapes,
    extract_regions,
    extract_vintages,
    extract_appellations,
)
from src.utils import logger


@dataclass
class QueryAnalysis:
    """
    Analysis of a user query for metadata filtering.

    Attributes:
        original_query: The original user query.
        grapes: Grape varieties detected in query.
        regions: Wine regions detected in query.
        vintages: Vintage years detected in query.
        appellations: Wine appellations detected in query.
        has_filters: Whether any filterable entities were found.
    """
    original_query: str
    grapes: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    vintages: List[str] = field(default_factory=list)
    appellations: List[str] = field(default_factory=list)

    @property
    def has_filters(self) -> bool:
        """Check if any filterable entities were detected."""
        return bool(self.grapes or self.regions or self.vintages or self.appellations)

    def to_chroma_filter(self, operator: str = "$or") -> Dict[str, Any] | None:
        """
        Convert to ChromaDB where filter.

        Args:
            operator: How to combine filters ("$or" or "$and").

        Returns:
            ChromaDB where filter dict, or None if no filters.
        """
        if not self.has_filters:
            return None

        conditions = []

        # Build conditions for each entity type
        for grape in self.grapes:
            conditions.append({"grapes": {"$contains": grape}})

        for region in self.regions:
            conditions.append({"regions": {"$contains": region}})

        for vintage in self.vintages:
            conditions.append({"vintages": {"$contains": vintage}})

        for appellation in self.appellations:
            conditions.append({"appellations": {"$contains": appellation}})

        if len(conditions) == 1:
            return conditions[0]

        return {operator: conditions}

    def get_boost_terms(self) -> List[str]:
        """Get terms that should boost relevance if found in chunks."""
        terms = []
        terms.extend(self.grapes)
        terms.extend(self.regions)
        terms.extend(self.vintages)
        terms.extend(self.appellations)
        return terms


def analyze_query(query: str) -> QueryAnalysis:
    """
    Analyze a user query to extract wine entities for filtering.

    Args:
        query: User's natural language query.

    Returns:
        QueryAnalysis with detected entities.
    """
    # Extract entities using existing extractors
    grapes = list(extract_grapes(query))
    regions = list(extract_regions(query))
    vintages = list(extract_vintages(query))
    appellations = list(extract_appellations(query))

    analysis = QueryAnalysis(
        original_query=query,
        grapes=grapes,
        regions=regions,
        vintages=vintages,
        appellations=appellations,
    )

    if analysis.has_filters:
        logger.debug(
            f"Query analysis: grapes={grapes}, regions={regions}, "
            f"vintages={vintages}, appellations={appellations}"
        )

    return analysis


def boost_by_metadata_match(
    docs: List[Dict[str, Any]],
    analysis: QueryAnalysis,
    boost_factor: float = 0.1,
) -> List[Dict[str, Any]]:
    """
    Boost document scores based on metadata matches.

    Documents whose metadata matches query entities get a score boost.

    Args:
        docs: Retrieved documents with 'similarity' scores.
        analysis: Query analysis with detected entities.
        boost_factor: Score boost per matching entity (default: 0.1).

    Returns:
        Documents with boosted scores, re-sorted by score.
    """
    if not analysis.has_filters or not docs:
        return docs

    boosted = []
    for doc in docs:
        doc_copy = doc.copy()
        metadata = doc_copy.get('metadata', {})
        similarity = doc_copy.get('similarity', 0.5)

        # Count metadata matches
        matches = 0

        doc_grapes = metadata.get('grapes', '').lower()
        for grape in analysis.grapes:
            if grape.lower() in doc_grapes:
                matches += 1

        doc_regions = metadata.get('regions', '').lower()
        for region in analysis.regions:
            if region.lower() in doc_regions:
                matches += 1

        doc_vintages = metadata.get('vintages', '')
        for vintage in analysis.vintages:
            if vintage in doc_vintages:
                matches += 1

        doc_appellations = metadata.get('appellations', '').lower()
        for appellation in analysis.appellations:
            if appellation.lower() in doc_appellations:
                matches += 1

        # Apply boost (capped at 1.0)
        boosted_similarity = min(1.0, similarity + (matches * boost_factor))
        doc_copy['similarity'] = boosted_similarity
        doc_copy['metadata_matches'] = matches

        boosted.append(doc_copy)

    # Re-sort by boosted similarity
    boosted.sort(key=lambda x: x.get('similarity', 0), reverse=True)

    total_matches = sum(d.get('metadata_matches', 0) for d in boosted)
    if total_matches > 0:
        logger.debug(f"Boosted {total_matches} metadata matches across {len(boosted)} docs")

    return boosted

