import os
import re
from io import BytesIO
from pathlib import Path

import pandas as pd
from omegaconf import DictConfig, OmegaConf


def find_project_root(marker="pyproject.toml"):
    """
    Walks up from the current file to find the project root.
    The marker can be a file or folder like '.git' or 'pyproject.toml'
    """
    current_path = os.path.abspath(os.getcwd())
    while current_path != os.path.dirname(current_path):
        if marker in os.listdir(current_path):
            return current_path
        current_path = os.path.dirname(current_path)
    raise FileNotFoundError(f"Project root with {marker} not found.")


def get_config() -> DictConfig:
    """Returns the app config object."""
    cfg = OmegaConf.load(Path(find_project_root()) / "app_config.yaml")
    cfg.data.local_path = Path(find_project_root()) / cfg.data.local_path
    cfg.data.qa_pairs = Path(find_project_root()) / cfg.data.qa_pairs

    return cfg


def parse_schema_json(schema: dict) -> list[tuple]:
    """Parses a JSON schema and returns a compressed version for displaying."""
    tables = schema["tables"]
    dfs = []
    for table in tables:
        df = pd.DataFrame(
            {
                "Name": [col.get("column_name") for col in table["columns"]],
                "Type": [col.get("column_type") for col in table["columns"]],
                "Description": [col.get("column_description") for col in table["columns"]],
            }
        )
        dfs.append((table["table_name"], df))

    return dfs


def df_to_excel(df: pd.DataFrame):
    """Convert dataframe to Excel."""
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="Sheet1")
    workbook = writer.book
    worksheet = writer.sheets["Sheet1"]
    format1 = workbook.add_format({"num_format": "0.00"})
    worksheet.set_column("A:A", None, format1)
    writer.close()
    processed_data = output.getvalue()

    return processed_data


def is_valid_sql(text: str) -> bool:    
    """Checks if the input text contains SQL.
    Currently only select whether a query contains a SELECT statement.
    Can be improved in the future."""
    if not isinstance(text, str):
        return False
    return bool(re.search(r"\bSELECT\b", text, re.IGNORECASE))
