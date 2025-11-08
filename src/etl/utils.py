"""Utility functions for ETL pipelines."""
import html
import hashlib
from difflib import SequenceMatcher
from datetime import datetime
from typing import Optional
from dateutil import parser


# Wine type mapping from various formats to standardized types
WINE_TYPE_MAP = {
    # Vivino formats
    'Red Wine': 'Red',
    'White Wine': 'White',
    'Rosé Wine': 'Rosé',
    'Sparkling': 'Sparkling',
    'Dessert Wine': 'Dessert',
    'Fortified Wine': 'Fortified',

    # CellarTracker formats
    'Red': 'Red',
    'White': 'White',
    'Rosé': 'Rosé',
    'Dessert': 'Dessert',
    'Fortified': 'Fortified',
}

COUNTRY_MAP = {
    "ro": "Romania",
    "fr": "France",
    "it": "Italy",
    "es": "Spain",
    "de": "Germany",
    "pt": "Portugal",
    "us": "United States",
    "md": "Moldova",
}


def normalize_wine_type(type_str: str) -> str:
    """
    Standardize wine type to unified format.
    """
    if not type_str:
        return "Red"

    return WINE_TYPE_MAP.get(type_str.strip(), "Red")


def clean_text(text: str) -> str | None:
    """
    Clean and normalize text.
    """
    if not text or text.strip() == "" or text.strip().lower() == "unknown":
        return None
    text = html.unescape(text)
    text = text.strip()

    return text if text else None


def parse_country(country_str: str) -> str | None:
    """
    Parse country name from various formats.
    """
    if not country_str or country_str.strip() == "":
        return None
    country_str = clean_text(country_str)
    if country_str in COUNTRY_MAP.keys():
        return COUNTRY_MAP[country_str]
    return country_str


def parse_date(date_str: str) -> str | None:
    """
    Parse various date formats to YYYY-MM-DD.
    """
    if not date_str:
        return None

    try:
        dt = parser.parse(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        return None


def parse_vintage(vintage_str: str) -> Optional[int]:
    """
    Parse vintage year from string.
    """
    if not vintage_str or vintage_str.strip() == "":
        return None

    try:
        vintage = int(vintage_str.strip())
        if 1900 <= vintage <= datetime.now().year + 2:
            return vintage
        return None
    except:
        return None


def parse_drinking_window(window_str: str, end_str: str | None = None) -> tuple[Optional[int], Optional[int]]:
    """
    Parse drinking window from various formats.

    Supports:
    - Vivino format: "2025 2027" (single string with space)
    - CellarTracker format: separate start and end parameters

    Args:
        window_str: Drinking window string from Vivino, or start year from CellarTracker
        end_str: Optional end year (for CellarTracker format)

    Returns:
        Tuple of (start_year, end_year) or (None, None)
    """
    if not window_str or window_str.strip() == '':
        return None, None

    try:
        # If end_str is provided, use CellarTracker format
        if end_str:
            start = int(window_str.strip()) if window_str else None
            end = int(end_str.strip()) if end_str else None
            return start, end

        # Otherwise try Vivino format (space-separated)
        parts = window_str.strip().split()
        if len(parts) == 2:
            start = int(parts[0])
            end = int(parts[1])
            return start, end
        elif len(parts) == 1:
            year = int(parts[0])
            return year, year
    except:
        pass

    return None, None


def string_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings (0-1 scale).
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def normalize_rating(rating: float, source: str) -> int | None:
    """
    Normalize ratings to 0-100 scale.
    """
    if rating is None:
        return None

    try:
        if source == 'vivino':
            # Vivino uses 0-5 scale, convert to 0-100
            # TODO: log scale conversion later
            return int((float(rating) / 5.0) * 100)
        elif source == 'cellar_tracker':
            # CellarTracker already uses 0-100
            return int(rating)
    except:
        return None

    return None


def generate_external_id(winery: str, wine_name: str, vintage: int | None) -> str:
    """
    Generate a consistent external ID for Vivino wines.
    """
    vintage_str = str(vintage) if vintage else "NV"
    key = f"{winery}_{wine_name}_{vintage_str}".lower()
    md5_hash = hashlib.md5(key.encode()).hexdigest()
    return str(int(md5_hash, 16) % (2**32))



