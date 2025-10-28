"""Utility functions for ETL processes."""
import html
import hashlib
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


def normalize_wine_type(type_str: str) -> str:
    """
    Standardize wine type to unified format.

    Args:
        type_str: Wine type string from source

    Returns:
        Standardized wine type
    """
    if not type_str:
        return 'Red'

    return WINE_TYPE_MAP.get(type_str.strip(), 'Red')


def clean_text(text: str) -> Optional[str]:
    """
    Clean and normalize text.

    Args:
        text: Raw text string

    Returns:
        Cleaned text or None if empty/unknown
    """
    if not text or text.strip() == '' or text.strip().lower() == 'unknown':
        return None

    # Decode HTML entities
    text = html.unescape(text)

    # Strip whitespace
    text = text.strip()

    return text if text else None


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse various date formats to YYYY-MM-DD.

    Args:
        date_str: Date string in various formats

    Returns:
        ISO format date string (YYYY-MM-DD) or None
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

    Args:
        vintage_str: Vintage string (may be empty for NV wines)

    Returns:
        Vintage year as integer or None for NV wines
    """
    if not vintage_str or vintage_str.strip() == '':
        return None

    try:
        vintage = int(vintage_str.strip())
        # Sanity check: wine vintage should be between 1900 and current year + 2
        if 1900 <= vintage <= datetime.now().year + 2:
            return vintage
        return None
    except:
        return None


def parse_drinking_window(window_str: str) -> tuple[Optional[int], Optional[int]]:
    """
    Parse drinking window from Vivino format (e.g., "2025 2027").

    Args:
        window_str: Drinking window string from Vivino

    Returns:
        Tuple of (start_year, end_year) or (None, None)
    """
    if not window_str or window_str.strip() == '':
        return None, None

    try:
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


def normalize_rating(rating: float, source: str) -> Optional[int]:
    """
    Normalize ratings to 0-100 scale.

    Args:
        rating: Rating value
        source: Source of rating ('vivino' or 'cellar_tracker')

    Returns:
        Rating on 0-100 scale or None
    """
    if rating is None:
        return None

    try:
        if source == 'vivino':
            # Vivino uses 0-5 scale, convert to 0-100
            return int((float(rating) / 5.0) * 100)
        elif source == 'cellar_tracker':
            # CellarTracker already uses 0-100
            return int(rating)
    except:
        return None

    return None


def generate_external_id(winery: str, wine_name: str, vintage: Optional[int]) -> str:
    """
    Generate a consistent external ID for Vivino wines.

    Args:
        winery: Winery/producer name
        wine_name: Wine name
        vintage: Vintage year (can be None)

    Returns:
        MD5 hash as external ID
    """
    vintage_str = str(vintage) if vintage else 'NV'
    key = f"{winery}_{wine_name}_{vintage_str}".lower()
    return hashlib.md5(key.encode()).hexdigest()


def normalize_string_for_comparison(s: str) -> str:
    """
    Normalize string for fuzzy matching.

    Args:
        s: String to normalize

    Returns:
        Normalized string
    """
    import unicodedata

    if not s:
        return ''

    # Remove accents
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')

    # Lowercase and remove extra spaces
    s = ' '.join(s.lower().split())

    return s

