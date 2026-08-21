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
        "Dec 2012" -> 2012
        "Mar-13"   -> 2013
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

    # Four-digit year
    match = re.search(r"(19|20)\d{2}", text)

    if match:
        return int(match.group())

    # Two-digit year such as Mar-13 or Mar 13
    match = re.search(
        r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[-\s]?(\d{2})$",
        text,
    )

    if match:
        year = int(match.group(1))

        # Financial datasets:
        # 00-29 -> 2000-2029
        # 30-99 -> 1930-1999
        return 2000 + year if year <= 29 else 1900 + year

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

    # Preserve internal spaces, as required by the tests.
    text = re.sub(r"\s+", " ", text)

    return text