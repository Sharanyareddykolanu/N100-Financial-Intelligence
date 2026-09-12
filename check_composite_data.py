import sqlite3
import pandas as pd

from src.analytics.composite_score import (
    calculate_composite_score
)


conn = sqlite3.connect("nifty100.db")


query = """
SELECT
    fr.company_id,
    fr.year,

    -- Existing ratio metrics
    fr.return_on_equity_pct,
    fr.net_profit_margin_pct,
    fr.debt_to_equity,
    fr.interest_coverage,
    fr.free_cash_flow_cr,
    fr.cash_from_operations_cr,
    fr.revenue_cagr_5yr,
    fr.pat_cagr_5yr,

    -- Profit & Loss
    pl.operating_profit,
    pl.net_profit,
    pl.sales,

    -- Balance Sheet
    bs.total_equity,
    bs.debt,

    -- Company information
    c.company_name,
    c.ticker,
    cs.sector

FROM financial_ratios fr

LEFT JOIN company_profit_loss pl
    ON fr.company_id = pl.company_id
    AND fr.year = pl.year

LEFT JOIN company_balance_sheet bs
    ON fr.company_id = bs.company_id
    AND fr.year = bs.year

LEFT JOIN companies c
    ON fr.company_id = c.company_id

LEFT JOIN company_sector cs
    ON fr.company_id = cs.company_id

ORDER BY fr.company_id, fr.year
"""


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

df = pd.read_sql_query(
    query,
    conn
)


print("=" * 70)
print("COMPOSITE SCORE INPUT DATA")
print("=" * 70)

print(f"Rows: {len(df)}")
print(f"Companies: {df['company_id'].nunique()}")


# ---------------------------------------------------------
# Required input validation
# ---------------------------------------------------------

required = [
    "return_on_equity_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "interest_coverage",
    "free_cash_flow_cr",
    "cash_from_operations_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit",
    "net_profit",
    "total_equity",
    "debt",
    "sector",
]


print("\nRequired columns:")

for column in required:
    print(
        f"{column}: "
        f"{df[column].notna().sum()} available"
    )


print("\nSample:")
print(
    df.head().to_string()
)


# ---------------------------------------------------------
# Calculate composite score
# ---------------------------------------------------------

scored_df = calculate_composite_score(df)


print("\n" + "=" * 70)
print("COMPOSITE SCORE RESULTS")
print("=" * 70)


score_count = (
    scored_df["composite_score"]
    .notna()
    .sum()
)

print(
    f"Composite scores available: "
    f"{score_count}"
)


print(
    f"Minimum score: "
    f"{scored_df['composite_score'].min():.2f}"
)


print(
    f"Maximum score: "
    f"{scored_df['composite_score'].max():.2f}"
)


print(
    f"Average score: "
    f"{scored_df['composite_score'].mean():.2f}"
)


# ---------------------------------------------------------
# Validate score range
# ---------------------------------------------------------

invalid_scores = scored_df[
    (scored_df["composite_score"] < 0)
    | (scored_df["composite_score"] > 100)
]


print(
    f"Invalid scores outside 0-100: "
    f"{len(invalid_scores)}"
)


# ---------------------------------------------------------
# Top 10 companies
# ---------------------------------------------------------

print("\nTop 10:")


top_columns = [
    "company_id",
    "year",
    "company_name",
    "sector",
    "composite_score",
]


top_10 = (
    scored_df[top_columns]
    .sort_values(
        "composite_score",
        ascending=False
    )
    .head(10)
)


print(
    top_10.to_string(
        index=False
    )
)


conn.close()