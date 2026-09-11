import sys
from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st
import plotly.express as px


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"

st.title("Sector Analysis")
st.caption("Compare companies within a selected sector")


def read_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


# ---------------------------------------------------------
# Load company + sector data
# ---------------------------------------------------------

companies = read_query(
    """
    SELECT
        c.company_id,
        c.company_name,
        c.ticker,
        s.sector
    FROM companies c
    LEFT JOIN company_sector s
        ON c.company_id = s.company_id
    WHERE s.sector IS NOT NULL
    ORDER BY c.company_name
    """

)

if companies.empty:
    st.warning("No sector data available.")
    st.stop()


sectors = sorted(
    companies["sector"].dropna().unique().tolist()
)

selected_sector = st.selectbox(
    "Select Sector",
    sectors
)


sector_companies = companies[
    companies["sector"] == selected_sector
].copy()


# ---------------------------------------------------------
# Load latest financial data
# ---------------------------------------------------------

ratios = read_query(
    """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        free_cash_flow_cr
    FROM financial_ratios
    """
)

valuation = read_query(
    """
    SELECT
        company_id,
        year,
        market_cap,
        pe_ratio,
        pb_ratio
    FROM company_valuation
    """
)


if ratios.empty:
    st.warning("Financial ratio data is not available.")
    st.stop()


latest_ratio_year = ratios["year"].max()
latest_valuation_year = valuation["year"].max()


ratios = ratios[
    ratios["year"] == latest_ratio_year
].copy()

valuation = valuation[
    valuation["year"] == latest_valuation_year
].copy()


data = sector_companies.merge(
    ratios,
    on="company_id",
    how="left"
)

data = data.merge(
    valuation,
    on="company_id",
    how="left"
)


data["return_on_equity_pct"] = pd.to_numeric(
    data["return_on_equity_pct"],
    errors="coerce"
)

data["market_cap"] = pd.to_numeric(
    data["market_cap"],
    errors="coerce"
)


data = data.dropna(
    subset=[
        "return_on_equity_pct",
        "market_cap"
    ]
)


# ---------------------------------------------------------
# Bubble Chart
# ---------------------------------------------------------

st.markdown(
    f"### {selected_sector} — Company Comparison"
)

if data.empty:
    st.info("No complete data available for this sector.")
else:

    fig = px.scatter(
        data,
        x="revenue_cagr_5yr"
        if "revenue_cagr_5yr" in data.columns
        else "market_cap",
        y="return_on_equity_pct",
        size="market_cap",
        hover_name="company_name",
        hover_data=["ticker"],
        title="Revenue vs ROE"
    )

    fig.update_layout(
        height=550,
        xaxis_title="Revenue / Growth",
        yaxis_title="ROE (%)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ---------------------------------------------------------
# Sector Median KPIs
# ---------------------------------------------------------

st.markdown("### Sector Median KPIs")


kpi_data = data.copy()

median_roe = kpi_data["return_on_equity_pct"].median()

median_market_cap = kpi_data["market_cap"].median()

median_pe = (
    kpi_data["pe_ratio"].median()
    if "pe_ratio" in kpi_data.columns
    else None
)

median_pb = (
    kpi_data["pb_ratio"].median()
    if "pb_ratio" in kpi_data.columns
    else None
)


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Median ROE",
    f"{median_roe:.2f}%"
)

col2.metric(
    "Median Market Cap",
    f"{median_market_cap:,.0f}"
)

col3.metric(
    "Median P/E",
    "N/A" if pd.isna(median_pe) else f"{median_pe:.2f}"
)

col4.metric(
    "Median P/B",
    "N/A" if pd.isna(median_pb) else f"{median_pb:.2f}"
)


# ---------------------------------------------------------
# Median Bar Chart
# ---------------------------------------------------------

median_chart = pd.DataFrame(
    {
        "Metric": [
            "ROE (%)",
            "P/E",
            "P/B"
        ],
        "Median": [
            median_roe,
            median_pe,
            median_pb
        ]
    }
).dropna()


if not median_chart.empty:

    fig2 = px.bar(
        median_chart,
        x="Metric",
        y="Median",
        title="Sector Median Metrics"
    )

    fig2.update_layout(
        height=400
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )


st.info(
    f"Latest available ratio year: {latest_ratio_year}. "
    f"Latest available valuation year: {latest_valuation_year}."
)
