import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"

st.title("Capital Allocation Map")
st.caption("Group companies by their capital allocation pattern")


def read_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


companies = read_query(
    """
    SELECT company_id, company_name, ticker, sector
    FROM companies
    ORDER BY company_name
    """
)

if companies.empty:
    st.warning("No company data available.")
    st.stop()


# Capital allocation patterns
patterns = [
    "Growth",
    "Dividend",
    "Debt Reduction",
    "Buyback",
    "Capex Heavy",
    "Cash Rich",
    "Balanced",
    "Mixed"
]


# Use available financial data
ratios = read_query(
    """
    SELECT
        company_id,
        year,
        free_cash_flow_cr,
        debt_to_equity,
        revenue_cagr_5yr
    FROM financial_ratios
    """
)

valuation = read_query(
    """
    SELECT
        company_id,
        year,
        dividend_yield,
        market_cap
    FROM company_valuation
    """
)


if not ratios.empty:
    latest_ratio_year = ratios["year"].max()

    ratios = ratios[
        ratios["year"] == latest_ratio_year
    ].copy()

else:
    latest_ratio_year = None


if not valuation.empty:
    latest_valuation_year = valuation["year"].max()

    valuation = valuation[
        valuation["year"] == latest_valuation_year
    ].copy()

else:
    latest_valuation_year = None


data = companies.merge(
    ratios,
    on="company_id",
    how="left"
)

data = data.merge(
    valuation,
    on="company_id",
    how="left"
)


for column in [
    "free_cash_flow_cr",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "dividend_yield",
    "market_cap"
]:
    if column in data.columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )


def classify(row):

    growth = row.get("revenue_cagr_5yr")
    dividend = row.get("dividend_yield")
    debt = row.get("debt_to_equity")
    fcf = row.get("free_cash_flow_cr")

    if pd.notna(growth) and growth >= 15:
        return "Growth"

    if pd.notna(dividend) and dividend >= 3:
        return "Dividend"

    if pd.notna(debt) and debt <= 0.1:
        return "Debt Reduction"

    if pd.notna(fcf) and fcf > 0 and pd.notna(growth) and growth >= 8:
        return "Capex Heavy"

    if pd.notna(fcf) and fcf > 0 and pd.notna(debt) and debt < 0.5:
        return "Cash Rich"

    if pd.notna(growth) and pd.notna(debt):
        return "Balanced"

    return "Mixed"


data["pattern"] = data.apply(
    classify,
    axis=1
)


# ---------------------------------------------------------
# Treemap
# ---------------------------------------------------------

st.markdown("### Capital Allocation Patterns")

treemap_data = (
    data.groupby("pattern")
    .size()
    .reset_index(name="companies")
)


fig = px.treemap(
    treemap_data,
    path=["pattern"],
    values="companies",
    title="Companies by Capital Allocation Pattern"
)

fig.update_layout(
    height=550
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ---------------------------------------------------------
# Pattern Selection
# ---------------------------------------------------------

selected_pattern = st.selectbox(
    "Select a Pattern",
    patterns
)


selected_companies = data[
    data["pattern"] == selected_pattern
][
    [
        "company_name",
        "ticker",
        "sector"
    ]
].sort_values("company_name")


st.markdown(
    f"### Companies — {selected_pattern}"
)

st.dataframe(
    selected_companies,
    use_container_width=True,
    hide_index=True
)


st.info(
    "Capital allocation patterns are derived from available "
    "growth, dividend, debt and cash-flow indicators."
)