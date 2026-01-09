"""Module for loading and providing access to wine-related terminology data."""

from pathlib import Path

from src.utils import load_json


_DATA_DIR = Path(__file__).parent / "terminology"

GRAPE_SYNONYMS: dict[str, list[str]] = load_json(_DATA_DIR /_DATA_DIR / "grape_synonyms.json")
REGION_VARIATIONS: dict[str, list[str]] = load_json(_DATA_DIR /"region_variations.json")
CLASSIFICATIONS: dict[str, str] = load_json(_DATA_DIR /"classifications.json")
QUERY_EXPANSIONS: dict[str, str] = load_json(_DATA_DIR /"query_expansions.json")
MISSPELLINGS: dict[str, str] = load_json(_DATA_DIR /"misspellings.json")
WINE_APPELLATIONS: list[str] = load_json(_DATA_DIR /"wine_appellations.json")


# Producer name patterns (common prefixes in wine producer names)
PRODUCER_PREFIXES = [
    r"château",
    r"chateau",
    r"domaine",
    r"domain",
    r"maison",
    r"cave",
    r"caves",
    r"bodega",
    r"bodegas",
    r"cantina",
    r"tenuta",
    r"fattoria",
    r"podere",
    r"azienda",
    r"weingut",
    r"schloss",
    r"quinta",
    r"clos",
    r"mas",
    r"casa",
    r"vina",
    r"viña",
]

# Producer suffix patterns
PRODUCER_SUFFIXES = [
    r"winery",
    r"vineyards",
    r"vineyard",
    r"estate",
    r"estates",
    r"cellars",
    r"cellar",
    r"wines",
    r"wine\s+company",
    r"wine\s+co\.?",
]

# Build reverse lookup dictionaries for extraction
GRAPE_PATTERNS: dict[str, str] = {}
for canonical, synonyms in GRAPE_SYNONYMS.items():
    GRAPE_PATTERNS[canonical.lower()] = canonical
    for syn in synonyms:
        GRAPE_PATTERNS[syn.lower()] = canonical

REGION_PATTERNS: dict[str, str] = {}
for canonical, variations in REGION_VARIATIONS.items():
    REGION_PATTERNS[canonical.lower()] = canonical
    for var in variations:
        REGION_PATTERNS[var.lower()] = canonical

# Wine classification patterns
CLASSIFICATION_PATTERNS = set(CLASSIFICATIONS.keys())