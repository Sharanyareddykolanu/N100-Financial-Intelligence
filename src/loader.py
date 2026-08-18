from pathlib import Path
import pandas as pd


def load_excel(file_path, sheet_name=0):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    if path.suffix.lower() not in [".xlsx", ".xls"]:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    return pd.read_excel(path, sheet_name=sheet_name)