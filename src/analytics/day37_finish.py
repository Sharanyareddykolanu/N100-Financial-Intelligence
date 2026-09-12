import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

# ============================================================
# DAY 37 - FINAL COMPLETION
# Portfolio Statistics + Cluster Profiling
# ============================================================

DB_PATH = "nifty100.db"

Path("output").mkdir(exist_ok=True)
Path("reports").mkdir(exist_ok=True)

c = sqlite3.connect(DB_PATH)

# ------------------------------------------------------------
# 1. EXACT 92-COMPANY UNIVERSE
# ------------------------------------------------------------

sector_df = pd.read_sql_query("""
    SELECT company_id, sector
    FROM company_sector
    ORDER BY company_id
""", c)

# ------------------------------------------------------------
# 2. LATEST 2024 FINANCIAL RATIOS
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# 3. LATEST 2024 VALUATION
# ------------------------------------------------------------

valuation_df = pd.read_sql_query("""
    SELECT
        company_id,
        dividend_yield,
        market_cap
    FROM company_valuation
    WHERE year = 2024
""", c)

c.close()

# Merge
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
# 4. KPI LIST
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

# Sector median imputation
for col in kpi_columns:
    df[col] = df[col].fillna(
        df.groupby("sector")[col].transform("median")
    )
    df[col] = df[col].fillna(df[col].median())

# ============================================================
# PART A - PORTFOLIO STATISTICS
# ============================================================

stats = pd.DataFrame(index=kpi_columns)

stats["P10"] = df[kpi_columns].quantile(0.10)
stats["P25"] = df[kpi_columns].quantile(0.25)
stats["P50"] = df[kpi_columns].quantile(0.50)
stats["P75"] = df[kpi_columns].quantile(0.75)
stats["P90"] = df[kpi_columns].quantile(0.90)
stats["Mean"] = df[kpi_columns].mean()
stats["Std"] = df[kpi_columns].std()

stats.index.name = "KPI"
stats = stats.round(4)

stats.to_csv(
    "output/portfolio_stats.csv"
)

print("=" * 65)
print("PART A - PORTFOLIO STATISTICS")
print("=" * 65)

print("Companies:", len(df))
print("KPIs:", len(kpi_columns))
print("\nPortfolio statistics:")
print(stats)

print("\nSaved:")
print("output/portfolio_stats.csv")

# ============================================================
# PART B - CLUSTER PROFILING
# ============================================================

cluster_features = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct"
]

# Load Day 36 cluster labels
cluster_file = "output/cluster_labels.csv"

clusters = pd.read_csv(cluster_file)

print("\n" + "=" * 65)
print("PART B - CLUSTER PROFILING")
print("=" * 65)

# Rebuild FCF CAGR from cash flow data
c = sqlite3.connect(DB_PATH)

cashflow = pd.read_sql_query("""
    SELECT
        company_id,
        year,
        operating_cash_flow,
        investing_cash_flow
    FROM company_cashflow
    ORDER BY company_id, year
""", c)

c.close()

cashflow["fcf"] = (
    cashflow["operating_cash_flow"]
    + cashflow["investing_cash_flow"]
)

fcf_rows = []

for company_id, group in cashflow.groupby("company_id"):

    group = group.sort_values("year")

    valid = group.dropna(subset=["fcf"])

    if len(valid) >= 5:

        start = valid.iloc[-6]["fcf"] if len(valid) >= 6 else np.nan
        end = valid.iloc[-1]["fcf"]

        if pd.notna(start) and pd.notna(end) and start > 0 and end > 0:
            years = valid.iloc[-1]["year"] - valid.iloc[-6]["year"]

            if years > 0:
                cagr = ((end / start) ** (1 / years) - 1) * 100
            else:
                cagr = np.nan
        else:
            cagr = np.nan
    else:
        cagr = np.nan

    fcf_rows.append({
        "company_id": company_id,
        "fcf_cagr_5yr": cagr
    })

fcf_df = pd.DataFrame(fcf_rows)

# Get clustering features from financial ratios
c = sqlite3.connect(DB_PATH)

cluster_ratio_df = pd.read_sql_query("""
    SELECT
        company_id,
        return_on_equity_pct,
        debt_to_equity,
        revenue_cagr_5yr,
        operating_profit_margin_pct
    FROM financial_ratios
    WHERE year = 2024
""", c)

c.close()

profile_df = sector_df.merge(
    cluster_ratio_df,
    on="company_id",
    how="left"
)

profile_df = profile_df.merge(
    fcf_df,
    on="company_id",
    how="left"
)

# Keep EXACTLY 92 companies
profile_df = profile_df[
    profile_df["company_id"].isin(sector_df["company_id"])
].copy()

# Sector median imputation for cluster features
for col in cluster_features:
    profile_df[col] = profile_df[col].fillna(
        profile_df.groupby("sector")[col].transform("median")
    )
    profile_df[col] = profile_df[col].fillna(
        profile_df[col].median()
    )

# Merge Day 36 cluster labels
profile_df = profile_df.merge(
    clusters[
        ["company_id", "cluster_id", "cluster_name"]
    ],
    on="company_id",
    how="left"
)

# Validate
print("92-company profile rows:", len(profile_df))
print("Missing cluster IDs:", profile_df["cluster_id"].isna().sum())

# ------------------------------------------------------------
# Cluster statistics
# ------------------------------------------------------------

cluster_profile = profile_df.groupby("cluster_id")[
    cluster_features
].agg(["mean", "median"])

print("\nCluster Profiles:")
print(cluster_profile.round(2))

# Save detailed profile
cluster_profile.to_csv(
    "output/cluster_profiles.csv"
)

# ------------------------------------------------------------
# Descriptive cluster naming
# ------------------------------------------------------------

summary = profile_df.groupby("cluster_id")[
    cluster_features
].mean()

# Standardize cluster characteristics across clusters
z = summary.copy()

for col in cluster_features:
    std = z[col].std()

    if std == 0 or pd.isna(std):
        z[col] = 0
    else:
        z[col] = (z[col] - z[col].mean()) / std

# Scores
quality_score = (
    z["return_on_equity_pct"]
    + z["operating_profit_margin_pct"]
    - z["debt_to_equity"]
)

growth_score = (
    z["revenue_cagr_5yr"]
    + z["fcf_cagr_5yr"]
)

dividend_score = z["return_on_equity_pct"]

# Start with unique names
cluster_names = {}

remaining = list(summary.index)

# Highest quality
if remaining:
    cid = quality_score.loc[remaining].idxmax()
    cluster_names[cid] = "High-Quality Compounders"
    remaining.remove(cid)

# Highest growth
if remaining:
    cid = growth_score.loc[remaining].idxmax()
    cluster_names[cid] = "Emerging Growth"
    remaining.remove(cid)

# Highest dividend/defensive profile
if remaining:
    cid = dividend_score.loc[remaining].idxmax()
    cluster_names[cid] = "Defensive Dividend Payers"
    remaining.remove(cid)

# Highest leverage / weaker profile
if remaining:
    distressed_score = (
        z.loc[remaining, "debt_to_equity"]
        - z.loc[remaining, "return_on_equity_pct"]
        - z.loc[remaining, "operating_profit_margin_pct"]
    )

    cid = distressed_score.idxmax()
    cluster_names[cid] = "Distressed / Turnaround"
    remaining.remove(cid)

# Remaining cluster
if remaining:
    cluster_names[remaining[0]] = "Value Cyclicals"

# Apply names
profile_df["descriptive_cluster_name"] = profile_df[
    "cluster_id"
].map(cluster_names)

# Save company-level cluster profile
profile_df[
    [
        "company_id",
        "sector",
        "cluster_id",
        "descriptive_cluster_name"
    ] + cluster_features
].to_csv(
    "output/cluster_profile_companies.csv",
    index=False
)

# Save cluster name mapping
cluster_mapping = pd.DataFrame([
    {
        "cluster_id": cid,
        "descriptive_cluster_name": name
    }
    for cid, name in sorted(cluster_names.items())
])

cluster_mapping.to_csv(
    "output/cluster_names.csv",
    index=False
)

print("\nSuggested Cluster Names:")
print(cluster_mapping.to_string(index=False))

print("\nCluster Distribution:")
print(
    profile_df["descriptive_cluster_name"]
    .value_counts()
)

print("\nSaved:")
print("output/cluster_profiles.csv")
print("output/cluster_profile_companies.csv")
print("output/cluster_names.csv")

# ============================================================
# FINAL DAY 37 VALIDATION
# ============================================================

print("\n" + "=" * 65)
print("DAY 37 FINAL VALIDATION")
print("=" * 65)

print("Target companies              :", 92)
print("Actual companies              :", len(df))
print("Portfolio KPI count            :", len(kpi_columns))
print(
    "Portfolio stats rows            :",
    len(stats)
)
print(
    "Outlier report exists           :",
    Path("output/outlier_report.csv").exists()
)
print(
    "Correlation heatmap exists      :",
    Path("reports/correlation_heatmap.png").exists()
)
print(
    "Portfolio stats exists          :",
    Path("output/portfolio_stats.csv").exists()
)
print(
    "Cluster profiles exists         :",
    Path("output/cluster_profiles.csv").exists()
)

print("\nDAY 37 STATUS: COMPLETED")
print("=" * 65)