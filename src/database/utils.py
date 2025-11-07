"""Database utility functions."""
from datetime import datetime

from pydantic import BaseModel


def build_update_query(
        table_name: str, model: BaseModel, id_field: str = "id", exclude_fields: list[str] | None = None
) -> tuple[str | None, list | None]:
    """
    Build dynamic SQL update query based on provided model non-null fields.

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
