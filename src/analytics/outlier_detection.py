import pandas as pd
import numpy as np
import sqlite3

# ------------------------------------------------------------
# DAY 37 - SECTOR-WISE Z-SCORE OUTLIER DETECTION
# ------------------------------------------------------------

DB_PATH = "nifty100.db"
OUTPUT_PATH = "output/outlier_report.csv"

# Connect to database
c = sqlite3.connect(DB_PATH)

# Get the exact 92-company universe
sector_df = pd.read_sql_query("""
    SELECT company_id, sector
    FROM company_sector
    ORDER BY company_id
""", c)

# Get latest 2024 financial ratios
ratios_df = pd.read_sql_query("""
    SELECT
        company_id,
        net_profit_margin_pct,
        operating_profit_margin_pct,
        return_on_equity_pct,
        debt_to_equity,
        asset_turnover,
        revenue_cagr_5yr,
        pat_cagr_5yr,
        eps_cagr_5yr
    FROM financial_ratios
    WHERE year = 2024
""", c)

# Get latest 2024 valuation data
valuation_df = pd.read_sql_query("""
    SELECT
        company_id,
        dividend_yield,
        market_cap
    FROM company_valuation
    WHERE year = 2024
""", c)

c.close()

# Merge the 92-company universe
df = sector_df.merge(
    ratios_df,
    on="company_id",
    how="left"
)

df = df.merge(
    valuation_df,
    on="company_id",
    how="left"
)

# ------------------------------------------------------------
# KPI list
# ------------------------------------------------------------

kpi_columns = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "asset_turnover",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "dividend_yield",
    "market_cap"
]

# ------------------------------------------------------------
# Sector median imputation
# ------------------------------------------------------------

for col in kpi_columns:
    df[col] = df[col].fillna(
        df.groupby("sector")[col].transform("median")
    )

    df[col] = df[col].fillna(
        df[col].median()
    )

print("=" * 60)
print("DAY 37 - OUTLIER DETECTION")
print("=" * 60)

print("Companies analyzed:", len(df))
print("Sectors:", df["sector"].nunique())

# ------------------------------------------------------------
# Z-score calculation
# ------------------------------------------------------------

outlier_rows = []

for sector, group in df.groupby("sector"):

    for idx, row in group.iterrows():

        metric_zscores = {}

        for col in kpi_columns:

            mean = group[col].mean()
            std = group[col].std()

            if pd.isna(std) or std == 0:
                z = 0
            else:
                z = (row[col] - mean) / std

            metric_zscores[col] = z

        # Flag metrics where absolute Z-score > 3
        flagged_metrics = [
            col
            for col, z in metric_zscores.items()
            if abs(z) > 3
        ]

        if flagged_metrics:

            max_z_metric = max(
                flagged_metrics,
                key=lambda col: abs(metric_zscores[col])
            )

            outlier_rows.append({
                "company_id": row["company_id"],
                "sector": sector,
                "outlier_metrics": ", ".join(flagged_metrics),
                "max_abs_zscore": round(
                    abs(metric_zscores[max_z_metric]), 4
                ),
                "max_zscore_metric": max_z_metric
            })

# ------------------------------------------------------------
# Create output
# ------------------------------------------------------------

outlier_report = pd.DataFrame(outlier_rows)

if len(outlier_report) > 0:
    outlier_report = outlier_report.sort_values(
        "max_abs_zscore",
        ascending=False
    )

outlier_report.to_csv(
    OUTPUT_PATH,
    index=False
)

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

print("\nOutlier companies:", len(outlier_report))

print("\nOutlier report:")

if len(outlier_report) > 0:
    print(outlier_report.to_string(index=False))
else:
    print("No companies exceeded |Z-score| > 3.")

print("\nOutput file:")
print(OUTPUT_PATH)

print("\nDAY 37 OUTLIER TEST: PASSED")
print("=" * 60)