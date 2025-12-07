"""
Wine agent tools for RAG-based wine knowledge retrieval.

This module provides tools for querying the wine knowledge base
using the existing RAG pipeline (ChromaDB + LangChain).
"""

from typing import Optional
from langchain_core.tools import tool

from src.rag.retriever import ChromaRetriever
from src.utils.context_builder import build_context_from_chunks
from src.utils import initialize_chroma_client, get_config, logger


def _get_rag_retriever(n_results: int = 5) -> ChromaRetriever:
    """Helper function to initialize RAG retriever."""
    config = get_config()
    client = initialize_chroma_client(
        host=config.chroma.host,
        port=config.chroma.port
    )

    return ChromaRetriever(
        client=client,
        collection_name="wine_books",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        n_results=n_results
    )


@tool
def search_wine_knowledge(
    query: str,
    max_results: int = 5,
    include_sources: bool = True
) -> str:
    """Search wine knowledge base for general wine information.

    Retrieves relevant information from wine books and documents stored
    in the ChromaDB vector store. Use this for general wine education,
    wine region information, winemaking techniques, grape varieties, etc.

    Args:
        query: Question or topic to search for. Examples:
              - "What makes Barolo special?"
              - "Difference between Burgundy and Bordeaux"
              - "How is Champagne made?"
              - "Characteristics of Nebbiolo grape"
              - "Aging potential of Rioja Reserva"
        max_results: Maximum number of source chunks to retrieve (1-10).
                    More results = more context but longer response.
                    Default is 5.
        include_sources: Whether to include source citations in response.
                        If True, shows which wine books the information came from.

    Returns:
        String containing relevant information from wine knowledge base
        with source citations if requested.

    Example:
        >>> info = search_wine_knowledge("What is malolactic fermentation?")
        >>> info = search_wine_knowledge(
        ...     "Barolo aging requirements",
        ...     max_results=3
        ... )

    Notes:
        - Uses existing RAG pipeline (ChromaDB + sentence-transformers)
        - Searches wine books: Wine Folly, World Atlas of Wine, etc.
        - Completely free operation (local vector search)
        - Does NOT query user's personal cellar or taste data
        - Returns general wine knowledge, not personalized information
    """
    try:
        # Validate max_results
        max_results = min(max(max_results, 1), 10)

        # Get retriever and search
        retriever = _get_rag_retriever(n_results=max_results)
        retrieved_docs = retriever.retrieve(query)

        if not retrieved_docs:
            return "No relevant information found in the wine knowledge base for this query."

        # Build context with sources
        context = build_context_from_chunks(
            retrieved_docs,
            include_metadata=include_sources,
            include_similarity=False,
            max_chunks=max_results
        )

        logger.info(f"Retrieved {len(retrieved_docs)} documents for wine knowledge query")
        return context

    except Exception as e:
        logger.error(f"Error searching wine knowledge: {e}")
        return f"Error retrieving wine knowledge: {str(e)}"


@tool
def search_wine_region_info(region: str) -> str:
    """Search for detailed information about a specific wine region.

    Specialized search focused on wine region characteristics, history,
    terroir, climate, and notable wines.

    Args:
        region: Wine region name. Examples:
               - "Bordeaux"
               - "Burgundy"
               - "Barolo"
               - "Napa Valley"
               - "Rioja"
               - "Champagne"
               Can be broad (country/region) or specific (appellation).

    Returns:
        String containing detailed region information with source citations.

    Example:
        >>> info = search_wine_region_info("Burgundy")
        >>> info = search_wine_region_info("Barolo")

    Notes:
        - Optimized for region-specific queries
        - Uses semantic search with region-focused prompting
        - Completely free operation (local vector search)
        - Includes map references if available in source books
    """
    try:
        # Format query for region-specific search
        formatted_query = (
            f"Tell me about the {region} wine region: "
            f"climate, terroir, grape varieties, wine styles, characteristics, "
            f"sub-regions, and notable producers"
        )

        # Use higher n_results for comprehensive region info
        retriever = _get_rag_retriever(n_results=7)
        retrieved_docs = retriever.retrieve(formatted_query)

        if not retrieved_docs:
            return f"No information found about the {region} wine region."

        # Build context with sources
        context = build_context_from_chunks(
            retrieved_docs,
            include_metadata=True,
            include_similarity=False,
            max_chunks=7
        )

        logger.info(f"Retrieved {len(retrieved_docs)} documents for region: {region}")
        return context

    except Exception as e:
        logger.error(f"Error searching region info: {e}")
        return f"Error retrieving region information: {str(e)}"


@tool
def search_grape_variety_info(varietal: str) -> str:
    """Search for detailed information about a grape variety.

    Specialized search focused on grape variety characteristics,
    growing regions, wine styles, and tasting notes.

    Args:
        varietal: Grape variety name. Examples:
                 - "Pinot Noir"
                 - "Cabernet Sauvignon"
                 - "Chardonnay"
                 - "Nebbiolo"
                 - "Tempranillo"
                 - "Riesling"
                 Can include synonyms (e.g., "Syrah" or "Shiraz")

    Returns:
        String containing grape variety information with source citations.

    Example:
        >>> info = search_grape_variety_info("Nebbiolo")
        >>> info = search_grape_variety_info("Pinot Noir")

    Notes:
        - Optimized for grape variety queries
        - Includes both Old World and New World expressions
        - Completely free operation (local vector search)
        - May include historical information if available
    """
    try:
        # Format query for varietal-specific search
        formatted_query = (
            f"Tell me about the {varietal} grape variety: "
            f"characteristics, growing regions, climate preferences, "
            f"typical flavors, aging potential, winemaking techniques, "
            f"and notable wines"
        )

        # Use higher n_results for comprehensive varietal info
        retriever = _get_rag_retriever(n_results=6)
        retrieved_docs = retriever.retrieve(formatted_query)

        if not retrieved_docs:
            return f"No information found about the {varietal} grape variety."

        # Build context with sources
        context = build_context_from_chunks(
            retrieved_docs,
            include_metadata=True,
            include_similarity=False,
            max_chunks=6
        )

        logger.info(f"Retrieved {len(retrieved_docs)} documents for varietal: {varietal}")
        return context

    except Exception as e:
        logger.error(f"Error searching varietal info: {e}")
        return f"Error retrieving varietal information: {str(e)}"


@tool
def search_wine_term_definition(term: str) -> str:
    """Search for definition and explanation of wine terminology.

    Look up wine-specific terms, concepts, and jargon in the knowledge base.

    Args:
        term: Wine term to define. Examples:
             - "terroir"
             - "malolactic fermentation"
             - "sur lie aging"
             - "Grand Cru"
             - "batonnage"
             - "tannins"
             - "botrytis"
             - "skin contact"
             - "carbonic maceration"

    Returns:
        String containing definition and explanation with source citations.

    Example:
        >>> definition = search_wine_term_definition("terroir")
        >>> definition = search_wine_term_definition("malolactic fermentation")

    Notes:
        - Provides wine-specific definitions, not generic dictionary definitions
        - Includes context and examples
        - Completely free operation (local vector search)
        - Explains both traditional and modern winemaking terms
    """
    try:
        # Format query for definition search
        formatted_query = (
            f"What is {term}? Define and explain {term} in the context of wine, "
            f"including how it affects wine character and examples"
        )

        # Use moderate n_results for focused definitions
        retriever = _get_rag_retriever(n_results=4)
        retrieved_docs = retriever.retrieve(formatted_query)

        if not retrieved_docs:
            return f"No definition found for '{term}' in the wine knowledge base."

        # Build context with sources
        context = build_context_from_chunks(
            retrieved_docs,
            include_metadata=True,
            include_similarity=False,
            max_chunks=4
        )

        logger.info(f"Retrieved {len(retrieved_docs)} documents for term: {term}")
        return context

    except Exception as e:
        logger.error(f"Error searching term definition: {e}")
        return f"Error retrieving term definition: {str(e)}"

