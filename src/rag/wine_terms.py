"""Wine terminology for query normalization and expansion."""
from typing import Dict, List

# Grape variety synonyms - canonical form as key, variations as values
GRAPE_SYNONYMS: Dict[str, List[str]] = {
    "cabernet sauvignon": ["cab sauv", "cabernet", "cs", "cab"],
    "pinot noir": ["pinot", "pn", "pinot n"],
    "sauvignon blanc": ["sauv blanc", "sb"],
    "chardonnay": ["chard"],
    "riesling": ["ries"],
    "nebbiolo": ["nebb"],
    "sangiovese": ["sangio", "sangioveto"],
    "tempranillo": ["temp", "tempran", "tinto fino", "tinta roriz"],
    "grenache": ["garnacha", "garnatxa", "cannonau"],
    "syrah": ["shiraz"],
    "merlot": ["merl"],
    "malbec": ["cot", "auxerrois"],
    "pinot grigio": ["pinot gris", "pg"],
    "gewurztraminer": ["gewurz", "traminer"],
    "mourvedre": ["monastrell", "mataro"],
    "cabernet franc": ["cab franc", "cf"],
    "chenin blanc": ["chenin", "steen"],
    "gruner veltliner": ["gruner", "gv", "grüner veltliner"],
    "albarino": ["albariño"],
    "viognier": ["viog"],
}

# Region name variations
REGION_VARIATIONS: Dict[str, List[str]] = {
    "burgundy": ["bourgogne", "burgandy"],
    "champagne": ["champgne"],
    "bordeaux": ["bdx"],
    "tuscany": ["toscana"],
    "piedmont": ["piemonte"],
    "rioja": ["la rioja"],
    "rhone": ["rhône", "cotes du rhone", "côtes du rhône"],
    "napa": ["napa valley"],
    "sonoma": ["sonoma county", "sonoma coast"],
    "willamette": ["willamette valley"],
    "barossa": ["barossa valley"],
    "marlborough": ["marlboro"],
    "mosel": ["moselle"],
    "alsace": ["alsace"],
    "loire": ["loire valley"],
    "mendoza": ["mendoza argentina"],
    "stellenbosch": ["stellenbosch south africa"],
    "douro": ["douro valley"],
    "ribera del duero": ["ribera"],
    "priorat": ["priorato"],
}

# Wine classification abbreviations
CLASSIFICATIONS: Dict[str, str] = {
    "docg": "denominazione di origine controllata e garantita",
    "doc": "denominazione di origine controllata",
    "igt": "indicazione geografica tipica",
    "aoc": "appellation d'origine contrôlée",
    "aop": "appellation d'origine protégée",
    "ava": "american viticultural area",
    "vdp": "verband deutscher prädikatsweingüter",
    "gw": "grosses gewächs",
    "gg": "grosses gewächs",
    "gc": "grand cru",
    "1er cru": "premier cru",
    "do": "denominación de origen",
    "doca": "denominación de origen calificada",
}

# Query expansion - related terms for better retrieval
QUERY_EXPANSIONS: Dict[str, str] = {
    "barolo": "barolo nebbiolo piedmont italy docg langhe",
    "barbaresco": "barbaresco nebbiolo piedmont italy docg",
    "brunello": "brunello montalcino sangiovese tuscany italy docg",
    "burgundy red": "burgundy pinot noir bourgogne france cote de nuits cote de beaune",
    "burgundy white": "burgundy chardonnay bourgogne france cote de beaune meursault puligny",
    "champagne": "champagne sparkling france chardonnay pinot noir pinot meunier",
    "bordeaux red": "bordeaux cabernet merlot france medoc saint emilion pomerol",
    "bordeaux white": "bordeaux sauvignon blanc semillon graves pessac",
    "napa cabernet": "napa valley cabernet sauvignon california oakville rutherford",
    "chianti": "chianti sangiovese tuscany italy classico",
    "rioja": "rioja tempranillo spain crianza reserva gran reserva",
    "port": "port douro portugal fortified tawny ruby vintage lbv",
    "sauternes": "sauternes bordeaux dessert botrytis semillon barsac",
    "amarone": "amarone valpolicella veneto italy ripasso corvina",
    "chablis": "chablis chardonnay burgundy france",
    "sancerre": "sancerre sauvignon blanc loire france",
    "chateauneuf": "chateauneuf du pape rhone france grenache mourvedre syrah",
    "riesling german": "riesling germany mosel rheingau pfalz kabinett spatlese",
    "sherry": "sherry jerez spain fortified fino manzanilla oloroso",
    "prosecco": "prosecco glera veneto italy sparkling",
    "cava": "cava spain sparkling catalonia",
}

# Common misspellings
MISSPELLINGS: Dict[str, str] = {
    "cabernet savignon": "cabernet sauvignon",
    "chardonay": "chardonnay",
    "chardonney": "chardonnay",
    "pinot nior": "pinot noir",
    "reisling": "riesling",
    "sauvingon": "sauvignon",
    "shirahz": "shiraz",
    "malbac": "malbec",
    "sangiovesse": "sangiovese",
    "nebiolo": "nebbiolo",
    "tempranilo": "tempranillo",
    "burgandy": "burgundy",
    "bourdeaux": "bordeaux",
    "champaign": "champagne",
}


def normalize_query(query: str) -> str:
    """
    Normalize wine terminology in query.

    Performs:
    - Lowercase conversion
    - Misspelling correction
    - Synonym replacement with canonical terms
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

    # Replace grape synonyms with canonical terms
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

    # Replace region variations with canonical terms
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
    Add related wine terms to query for better retrieval coverage.

    Args:
        query: Normalized query string

    Returns:
        Query expanded with related terms
    """
    query_lower = query.lower()

    for key, expansion in QUERY_EXPANSIONS.items():
        if key in query_lower:
            # Add expansion terms that aren't already in query
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

