"""
Day 11 - Cash Flow KPIs & Capital Allocation

Implements:
- Free Cash Flow (FCF)
- CFO Quality Score
- CapEx Intensity
- FCF Conversion Rate
- Capital Allocation Pattern Classifier

Capital allocation patterns:
(+,-,-) = Reinvestor
(+,-,-) with high CFO/PAT = Shareholder Returns
(+,+,-) = Liquidating Assets
(-,+,+) = Distress Signal
(-,-,+) = Growth Funded by Debt
(+,+,+) = Cash Accumulator
(-,-,-) = Pre-Revenue
(+,-,+) = Mixed
"""


def free_cash_flow(operating_activity, investing_activity):
    """
    Free Cash Flow = Operating Activity + Investing Activity.

    Negative FCF is allowed.
    Returns None when either value is unavailable.
    """
    if operating_activity is None or investing_activity is None:
        return None

    return operating_activity + investing_activity


def cfo_quality_score(cfo_values, pat_values):
    """
    Calculate the average CFO / PAT ratio over 5 years.

    Classification:
        > 1.0       = High Quality
        0.5 - 1.0   = Moderate
        < 0.5       = Accrual Risk

    Returns:
        (average_ratio, quality_label)

    Returns (None, None) when PAT is zero or insufficient
    valid data is available.
    """
    if cfo_values is None or pat_values is None:
        return None, None

    ratios = []

    for cfo, pat in zip(cfo_values[-5:], pat_values[-5:]):
        if cfo is None or pat is None or pat == 0:
            continue

        ratios.append(cfo / pat)

    if not ratios:
        return None, None

    average_ratio = sum(ratios) / len(ratios)

    if average_ratio > 1.0:
        label = "High Quality"
    elif average_ratio >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return average_ratio, label


def capex_intensity(investing_activity, sales):
    """
    CapEx Intensity = abs(Investing Activity) / Sales * 100.

    Classification:
        < 3%       = Asset Light
        3% - 8%    = Moderate
        > 8%       = Capital Intensive

    Returns:
        (percentage, classification)

    Returns (None, None) when sales is zero or unavailable.
    """
    if investing_activity is None or sales is None or sales == 0:
        return None, None

    intensity = abs(investing_activity) / sales * 100

    if intensity < 3:
        label = "Asset Light"
    elif intensity <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return intensity, label


def fcf_conversion_rate(fcf, operating_profit):
    """
    FCF Conversion Rate = FCF / Operating Profit * 100.

    Returns None when operating profit is zero or unavailable.
    """
    if fcf is None or operating_profit is None or operating_profit == 0:
        return None

    return (fcf / operating_profit) * 100


def _sign(value):
    """
    Convert a cash-flow value into its sign.

    Returns:
        "+" for positive
        "-" for negative
        "0" for zero
        None for unavailable
    """
    if value is None:
        return None

    if value > 0:
        return "+"
    if value < 0:
        return "-"
    return "0"


def classify_capital_allocation(
    cfo,
    cfi,
    cff,
    cfo_pat_ratio=None
):
    """
    Classify capital allocation using the signs of:
        CFO = Operating Cash Flow
        CFI = Investing Cash Flow
        CFF = Financing Cash Flow

    Special case:
        (+,-,-) with high CFO/PAT (> 1.0)
        = Shareholder Returns

    Otherwise:
        (+,-,-) = Reinvestor
        (+,+,-) = Liquidating Assets
        (-,+,+) = Distress Signal
        (-,-,+) = Growth Funded by Debt
        (+,+,+) = Cash Accumulator
        (-,-,-) = Pre-Revenue
        (+,-,+) = Mixed

    Returns "Unknown" when the combination is not defined.
    """
    pattern = (_sign(cfo), _sign(cfi), _sign(cff))

    if pattern == ("+", "-", "-"):
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            return "Shareholder Returns"
        return "Reinvestor"

    labels = {
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }

    return labels.get(pattern, "Unknown")


def capital_allocation_row(
    company_id,
    year,
    cfo,
    cfi,
    cff,
    cfo_pat_ratio=None
):
    """
    Generate one capital-allocation output row.
    """
    return {
        "company_id": company_id,
        "year": year,
        "cfo_sign": _sign(cfo),
        "cfi_sign": _sign(cfi),
        "cff_sign": _sign(cff),
        "pattern_label": classify_capital_allocation(
            cfo,
            cfi,
            cff,
            cfo_pat_ratio
        ),
    }
def generate_capital_allocation_csv(db_path, output_path):
    """Generate capital allocation CSV from company cash-flow data."""
    import csv
    import sqlite3
    from pathlib import Path

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    rows = conn.execute("""
               SELECT
            company_id,
            year,
            operating_cash_flow,
            investing_cash_flow,
            financing_cash_flow
        FROM company_cashflow
        ORDER BY company_id, year
    """).fetchall()

    conn.close()

    output_rows = []

    for company_id, year, cfo, cfi, cff in rows:
        output_rows.append(
            capital_allocation_row(
                company_id,
                year,
                cfo,
                cfi,
                cff
            )
        )

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "company_id",
                "year",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    return output_path
