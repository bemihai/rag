"""Database utility functions."""
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher

from pydantic import BaseModel


def build_update_query(
        table_name: str, model: BaseModel, id_field: str = "id", exclude_fields: list[str] | None = None
) -> tuple[str | None, list | None]:
    """
    Build dynamic SQL update query based on provided agents non-null fields.

    Args:
        table_name: Name of the database table.
        model: Model instance with updated data.
        id_field: Name of the ID field (default is "id", this is not updated).
        exclude_fields: List of fields to exclude from update.

    Returns:
        Tuple of SQL update query string and list of parameters, or None if no fields to update.
    """
    fields, params = [], []
    exclude_fields = exclude_fields or []
    exclude_fields.append(id_field)
    all_attrs = [f for f in model.model_fields.keys() if f not in exclude_fields]
    for attr in all_attrs:
        value = getattr(model, attr)
        if value:
            fields.append(f"{attr} = ?")
            params.append(value)

    if not fields:
        return None, None

    fields.append("updated_at = ?")
    params.append(datetime.now())
    params.append(getattr(model, id_field))
    set_clause = ", ".join(fields)

    return f"UPDATE {table_name} SET {set_clause} WHERE id = ?", params


def normalize_string(s: str) -> str:
    """
    Normalize string for comparison by removing accents and extra whitespace.

    Args:
        s: String to normalize

    Returns:
        Normalized string (lowercase, no accents, single spaces)
    """
    if not s:
        return ""

    # Remove accents
    s = "".join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )

    # Lowercase and remove extra spaces
    s = " ".join(s.lower().split())

    return s


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity ratio between 0.0 and 1.0
    """
    norm1 = normalize_string(str1)
    norm2 = normalize_string(str2)

    if not norm1 or not norm2:
        return 0.0

    return SequenceMatcher(None, norm1, norm2).ratio()