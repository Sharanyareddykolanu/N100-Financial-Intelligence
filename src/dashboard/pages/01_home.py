import sys
from pathlib import Path
import sqlite3

import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------
# FIX PYTHON IMPORT PATH
# ---------------------------------------------------------
SRC_PATH = Path(__file__).resolve().parents[2]

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dashboard.utils.db import get_companies, get_ratios


# ---------------------------------------------------------
# PAGE TITLE
# ---------------------------------------------------------
st.title("Nifty 100 Analytics")
st.subheader("Market Overview")


# ---------------------------------------------------------
# LOAD COMPANIES
# ---------------------------------------------------------
companies = get_companies()


# ---------------------------------------------------------
# YEAR SELECTOR
# ---------------------------------------------------------
year = st.sidebar.selectbox(
    "Select Year",
    list(range(2019, 2025)),
    index=5
)


# ---------------------------------------------------------
# LOAD FINANCIAL RATIOS FOR SELECTED YEAR
# ---------------------------------------------------------
# get_ratios() expects company_id, so load all ratios
# directly for the selected year.

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"

conn = sqlite3.connect(DB_PATH)

ratios = pd.read_sql_query(
    """
    SELECT *
    FROM financial_ratios
    WHERE year = ?
    """,
    conn,
    params=(year,)
)

conn.close()


# ---------------------------------------------------------
# MERGE COMPANY + RATIO DATA
# ---------------------------------------------------------
if not ratios.empty:
    data = companies.merge(
        ratios,
        on="company_id",
        how="inner"
    )
else:
    data = companies.copy()


# ---------------------------------------------------------
# HELPER FUNCTION
# ---------------------------------------------------------
def get_median(column):
    if column not in data.columns:
        return "N/A"

    values = pd.to_numeric(
        data[column],
        errors="coerce"
    ).dropna()

    if values.empty:
        return "N/A"

    return f"{values.median():.2f}"


# ---------------------------------------------------------
# AVERAGE ROE
# ---------------------------------------------------------
average_roe = "N/A"

if "return_on_equity_pct" in data.columns:

    roe_values = pd.to_numeric(
        data["return_on_equity_pct"],
        errors="coerce"
    ).dropna()

    if not roe_values.empty:
        average_roe = f"{roe_values.mean():.2f}%"


# ---------------------------------------------------------
# MEDIAN P/E
# ---------------------------------------------------------
conn = sqlite3.connect(DB_PATH)

valuation = pd.read_sql_query(
    """
    SELECT *
    FROM company_valuation
    WHERE year = ?
    """,
    conn,
    params=(year,)
)

conn.close()

median_pe = "N/A"

if not valuation.empty and "pe_ratio" in valuation.columns:

    pe_values = pd.to_numeric(
        valuation["pe_ratio"],
        errors="coerce"
    )

    pe_values = pe_values.replace(
        [float("inf"), -float("inf")],
        pd.NA
    ).dropna()

    if not pe_values.empty:
        median_pe = f"{pe_values.median():.2f}"


# ---------------------------------------------------------
# MEDIAN D/E
# ---------------------------------------------------------
median_de = get_median("debt_to_equity")


# ---------------------------------------------------------
# TOTAL COMPANIES
# ---------------------------------------------------------
total_companies = len(companies)


# ---------------------------------------------------------
# MEDIAN REVENUE CAGR
# ---------------------------------------------------------
median_revenue_cagr = get_median("revenue_cagr_5yr")

if median_revenue_cagr != "N/A":
    median_revenue_cagr = median_revenue_cagr + "%"


# ---------------------------------------------------------
# DEBT-FREE COMPANIES
# ---------------------------------------------------------
debt_free_count = 0

if "debt_to_equity" in data.columns:

    de_values = pd.to_numeric(
        data["debt_to_equity"],
        errors="coerce"
    )

    debt_free_count = int(
        (de_values <= 0).sum()
    )


# ---------------------------------------------------------
# KPI SECTION
# ---------------------------------------------------------
st.markdown("### Key Performance Indicators")

col1, col2, col3, col4, col5, col6 = st.columns(6)


with col1:
    st.metric(
        "Average ROE",
        average_roe
    )


with col2:
    st.metric(
        "Median P/E",
        median_pe
    )


with col3:
    st.metric(
        "Median D/E",
        median_de
    )


with col4:
    st.metric(
        "Total Companies",
        total_companies
    )


with col5:
    st.metric(
        "Median Revenue CAGR 5Y",
        median_revenue_cagr
    )


with col6:
    st.metric(
        "Debt-Free Companies",
        debt_free_count
    )


# ---------------------------------------------------------
# SECTOR BREAKDOWN
# ---------------------------------------------------------
st.markdown("### Sector Breakdown")

if "sector" in companies.columns:

    sector_data = (
        companies["sector"]
        .fillna("Unknown")
        .value_counts()
        .reset_index()
    )

    sector_data.columns = [
        "Sector",
        "Company Count"
    ]

    fig_sector = px.pie(
        sector_data,
        names="Sector",
        values="Company Count",
        hole=0.55,
        title=f"Companies by Sector — {year}"
    )

    fig_sector.update_traces(
        textposition="inside",
        textinfo="percent"
    )

    fig_sector.update_layout(
        height=500,
        legend_title="Sector"
    )

    st.plotly_chart(
        fig_sector,
        use_container_width=True
    )

else:

    st.warning(
        "Sector data is not available."
    )


# ---------------------------------------------------------
# TOP 5 COMPANIES
# ---------------------------------------------------------
st.markdown(
    "### Top 5 Companies by Composite Quality Score"
)

if "composite_quality_score" in data.columns:

    top5 = data[
        [
            "company_name",
            "ticker",
            "sector",
            "composite_quality_score"
        ]
    ].copy()

    top5["composite_quality_score"] = pd.to_numeric(
        top5["composite_quality_score"],
        errors="coerce"
    )

    top5 = (
        top5
        .dropna(
            subset=["composite_quality_score"]
        )
        .sort_values(
            "composite_quality_score",
            ascending=False
        )
        .head(5)
    )

    top5["composite_quality_score"] = (
        top5["composite_quality_score"].round(2)
    )

    st.dataframe(
        top5,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "Composite quality score is not available."
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")

st.caption(
    f"Nifty 100 Analytics • Selected Year: {year}"
)