import math
import re


def normalize_year(value):
    """
    Normalize financial year values to a four-digit year.

    Examples:
        2024       -> 2024
        "2024"     -> 2024
        "FY2024"   -> 2024
        "FY 2024"  -> 2024
        "2024-25"  -> 2024
    """

    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    match = re.search(r"(19|20)\d{2}", text)

    if match:
        return int(match.group())

    return None


def normalize_ticker(value):
    """
    Normalize stock ticker symbols.

    Examples:
        "tcs"       -> "TCS"
        " TCS "     -> "TCS"
        "infy.ns"   -> "INFY.NS"
    """

    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    return text