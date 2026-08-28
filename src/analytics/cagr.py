"""
Day 10 - CAGR Engine

Calculates CAGR for:
- Revenue
- PAT / Net Profit
- EPS

Supports:
- 3-year CAGR
- 5-year CAGR
- 10-year CAGR

Handles six edge cases:
- Positive + Positive
- Positive + Negative
- Negative + Positive
- Negative + Negative
- Zero base
- Insufficient data
"""


def calculate_cagr(start, end, years):
    """
    Calculate CAGR.

    CAGR = ((end / start) ** (1 / years) - 1) * 100

    Returns:
        (cagr_value, flag)

    Flags:
        None
        DECLINE_TO_LOSS
        TURNAROUND
        BOTH_NEGATIVE
        ZERO_BASE
        INSUFFICIENT
    """

    if years is None or years <= 0:
        return None, "INSUFFICIENT"

    if start is None or end is None:
        return None, "INSUFFICIENT"

    if start == 0:
        return None, "ZERO_BASE"

    if start > 0 and end > 0:
        cagr = ((end / start) ** (1 / years) - 1) * 100
        return cagr, None

    if start > 0 and end < 0:
        return None, "DECLINE_TO_LOSS"

    if start < 0 and end > 0:
        return None, "TURNAROUND"

    if start < 0 and end < 0:
        return None, "BOTH_NEGATIVE"

    return None, "INSUFFICIENT"


def _get_window_values(values, years):
    """
    Get start and end values for a CAGR window.

    A valid window requires at least years + 1 observations,
    because a 3-year CAGR needs a starting year and an ending
    year separated by 3 years.
    """
    if values is None:
        return None, None, "INSUFFICIENT"

    values = list(values)

    if len(values) < years + 1:
        return None, None, "INSUFFICIENT"

    return values[-(years + 1)], values[-1], None


def compute_window_cagr(values, years):
    """
    Compute CAGR for a specific time window.

    Example:
        3-year CAGR requires 4 annual observations.
    """
    start, end, flag = _get_window_values(values, years)

    if flag is not None:
        return None, flag

    return calculate_cagr(start, end, years)


def revenue_cagr(values):
    """
    Calculate Revenue CAGR for 3, 5 and 10 years.

    Returns a dictionary containing both values and flags.
    """
    result = {}

    for years in (3, 5, 10):
        value, flag = compute_window_cagr(values, years)
        result[f"revenue_cagr_{years}yr"] = value
        result[f"revenue_cagr_{years}yr_flag"] = flag

    return result


def pat_cagr(values):
    """
    Calculate PAT / Net Profit CAGR for 3, 5 and 10 years.

    Returns a dictionary containing both values and flags.
    """
    result = {}

    for years in (3, 5, 10):
        value, flag = compute_window_cagr(values, years)
        result[f"pat_cagr_{years}yr"] = value
        result[f"pat_cagr_{years}yr_flag"] = flag

    return result


def eps_cagr(values):
    """
    Calculate EPS CAGR for 3, 5 and 10 years.

    Returns a dictionary containing both values and flags.
    """
    result = {}

    for years in (3, 5, 10):
        value, flag = compute_window_cagr(values, years)
        result[f"eps_cagr_{years}yr"] = value
        result[f"eps_cagr_{years}yr_flag"] = flag

    return result


def all_growth_metrics(revenue, pat, eps):
    """
    Calculate all Revenue, PAT and EPS CAGR metrics.

    Returns one dictionary containing all CAGR values
    and their corresponding flags.
    """
    result = {}

    result.update(revenue_cagr(revenue))
    result.update(pat_cagr(pat))
    result.update(eps_cagr(eps))

    return result