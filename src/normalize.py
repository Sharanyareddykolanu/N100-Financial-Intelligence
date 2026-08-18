import math
import re


def normalize_year(value):
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value) if value.is_integer() else None

    text = str(value).strip().upper()

    if not text:
        return None

    match = re.search(r"(19|20)\d{2}", text)

    return int(match.group()) if match else None


def normalize_ticker(value):
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    return re.sub(r"\s+", " ", text)