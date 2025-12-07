"""
Wine agent tools package.

This package provides all tools for the wine agent, organized by functionality:
- cellar_tools: Wine cellar inventory and management
- taste_profile_tools: User preference analysis and recommendations
- pairing_tools: Food and wine pairing recommendations
- rag_tools: Wine knowledge base search (RAG)
"""

from typing import List
from langchain_core.tools import BaseTool

from .cellar_tools import (
    get_cellar_wines,
    get_wine_details,
    get_cellar_statistics,
    find_wines_by_location,
)

from .taste_profile_tools import (
    get_user_taste_profile,
    get_top_rated_wines,
    get_wine_recommendations_from_profile,
    analyze_rating_trends,
    compare_wine_to_profile,
)

from .pairing_tools import (
    get_food_pairing_wines,
    get_pairing_for_wine,
    get_wine_and_cheese_pairings,
    suggest_dinner_menu_with_wines,
)

from .rag_tools import (
    search_wine_knowledge,
    search_wine_region_info,
    search_grape_variety_info,
    search_wine_term_definition,
)


# Core tools for initial agent (Phase 1)
CORE_TOOLS: List[BaseTool] = [
    # Cellar management - most common queries
    get_cellar_wines,
    get_wine_details,

    # Taste profile - personalization
    get_user_taste_profile,

    # RAG - general knowledge
    search_wine_knowledge,

    # Food pairing - practical queries
    get_food_pairing_wines,
]

# Extended tools for Phase 2
EXTENDED_TOOLS: List[BaseTool] = [
    # Additional cellar tools
    get_cellar_statistics,
    find_wines_by_location,

    # Additional taste profile tools
    get_top_rated_wines,
    get_wine_recommendations_from_profile,
    compare_wine_to_profile,

    # Additional pairing tools
    get_pairing_for_wine,
    get_wine_and_cheese_pairings,

    # Additional RAG tools
    search_wine_region_info,
    search_grape_variety_info,
    search_wine_term_definition,
]

# All tools combined
ALL_TOOLS: List[BaseTool] = CORE_TOOLS + EXTENDED_TOOLS


def get_tools_for_phase(phase: int = 1) -> List[BaseTool]:
    """Get tools for specific implementation phase.

    Args:
        phase: Implementation phase number
               1 = Core tools only (5 tools)
               2 = All tools (17 tools)

    Returns:
        List of tool instances
    """
    if phase == 1:
        return CORE_TOOLS
    elif phase == 2:
        return ALL_TOOLS
    else:
        raise ValueError(f"Invalid phase: {phase}. Must be 1 or 2.")


__all__ = [
    # Core tools
    "get_cellar_wines",
    "get_wine_details",
    "get_user_taste_profile",
    "search_wine_knowledge",
    "get_food_pairing_wines",

    # Extended tools
    "get_cellar_statistics",
    "find_wines_by_location",
    "get_top_rated_wines",
    "get_wine_recommendations_from_profile",
    "analyze_rating_trends",
    "compare_wine_to_profile",
    "get_pairing_for_wine",
    "get_wine_and_cheese_pairings",
    "suggest_dinner_menu_with_wines",
    "search_wine_region_info",
    "search_grape_variety_info",
    "search_wine_term_definition",

    # Tool collections
    "CORE_TOOLS",
    "EXTENDED_TOOLS",
    "ALL_TOOLS",
    "get_tools_for_phase",
]

