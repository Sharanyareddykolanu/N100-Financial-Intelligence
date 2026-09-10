import sys
from pathlib import Path
import sqlite3

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Add src folder to Python path
SRC_PATH = Path(__file__).resolve().parents[2]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_pl,
    get_bs,
    get_cf,
)

st.title("Company Profile")

# ---------------------------------------------------------
# LOAD COMPANIES
# ---------------------------------------------------------

companies = get_companies()

if companies.empty:
    st.error("No company data available.")
    st.stop()

# ---------------------------------------------------------
# COMPANY SEARCH
# ---------------------------------------------------------

companies["search_text"] = (
    companies["company_name"].fillna("").astype(str)
    + " | "
    + companies["ticker"].fillna("").astype(str)
)

search = st.text_input(
    "Search Company",
    placeholder="Type company name or ticker..."
)

if search:
    matches = companies[
        companies["search_text"]
        .str.contains(search, case=False, na=False)
    ]
else:
    matches = companies

if matches.empty:
    st.warning("Ticker not found — please try another")
    st.stop()

# Autocomplete-style dropdown
options = matches["search_text"].tolist()

selected_company = st.selectbox(
    "Select Company",
    options
)

selected_ticker = selected_company.split(" | ")[-1]

company_row = companies[
    companies["ticker"] == selected_ticker
].iloc[0]

company_id = company_row["company_id"]
company_name = company_row["company_name"]

# ---------------------------------------------------------
# SECTOR
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"

conn = sqlite3.connect(DB_PATH)

sector_df = pd.read_sql_query(
    """
    SELECT sector
    FROM company_sector
    WHERE company_id = ?
    LIMIT 1
    """,
    conn,
    params=(company_id,)
)

conn.close()

if not sector_df.empty:
    sector = sector_df.iloc[0]["sector"]
else:
    sector = "Not available"

# ---------------------------------------------------------
# COMPANY CARD
# ---------------------------------------------------------

st.markdown("## Company Information")

info1, info2, info3 = st.columns(3)

with info1:
    st.markdown(f"### {company_name}")
    st.write(f"**NSE Ticker:** {selected_ticker}")

with info2:
    st.write(f"**Sector:** {sector}")
    st.write("**Sub-Sector:** Not available in current dataset")

with info3:
    st.write("**About:** Not available in current dataset")

st.markdown("---")

# ---------------------------------------------------------
# LOAD FINANCIAL DATA
# ---------------------------------------------------------

ratios = get_ratios(company_id)
pl = get_pl(company_id)
bs = get_bs(company_id)
cf = get_cf(company_id)

# Make sure data is sorted
ratios = ratios.sort_values("year")
pl = pl.sort_values("year")
bs = bs.sort_values("year")
cf = cf.sort_values("year")

# ---------------------------------------------------------
# LATEST YEAR
# ---------------------------------------------------------

latest_year = None

if not ratios.empty:
    latest_year = ratios["year"].max()
elif not pl.empty:
    latest_year = pl["year"].max()

latest_ratio = pd.DataFrame()

if latest_year is not None and not ratios.empty:
    latest_ratio = ratios[
        ratios["year"] == latest_year
    ]

# ---------------------------------------------------------
# KPI VALUES
# ---------------------------------------------------------

def get_value(column):
    if latest_ratio.empty:
        return "N/A"

    if column not in latest_ratio.columns:
        return "N/A"

    value = pd.to_numeric(
        latest_ratio.iloc[0][column],
        errors="coerce"
    )

    if pd.isna(value):
        return "N/A"

    return f"{value:.2f}"


roe = get_value("return_on_equity_pct")
npm = get_value("net_profit_margin_pct")
de = get_value("debt_to_equity")
revenue_cagr = get_value("revenue_cagr_5yr")

# ---------------------------------------------------------
# ROCE CALCULATION
# ---------------------------------------------------------

roce = "N/A"

if latest_year is not None and not pl.empty and not bs.empty:

    latest_pl = pl[
        pl["year"] == latest_year
    ]

    latest_bs = bs[
        bs["year"] == latest_year
    ]

    if not latest_pl.empty and not latest_bs.empty:

        operating_profit = pd.to_numeric(
            latest_pl.iloc[0]["operating_profit"],
            errors="coerce"
        )

        equity = pd.to_numeric(
            latest_bs.iloc[0]["total_equity"],
            errors="coerce"
        )

        debt = pd.to_numeric(
            latest_bs.iloc[0]["debt"],
            errors="coerce"
        )

        if (
            pd.notna(operating_profit)
            and pd.notna(equity)
            and pd.notna(debt)
            and (equity + debt) != 0
        ):
            roce_value = (
                operating_profit
                / (equity + debt)
                * 100
            )

            roce = f"{roce_value:.2f}"

# ---------------------------------------------------------
# FCF
# ---------------------------------------------------------

fcf = "N/A"

if not cf.empty:

    latest_cf = cf[
        cf["year"] == latest_year
    ]

    if not latest_cf.empty:

        fcf_value = pd.to_numeric(
            latest_cf.iloc[0]["free_cash_flow"],
            errors="coerce"
        )

        if pd.notna(fcf_value):
            fcf = f"{fcf_value:.2f}"

# ---------------------------------------------------------
# KPI TILES
# ---------------------------------------------------------

st.markdown(
    f"### Key Metrics — {latest_year if latest_year else 'Latest Year'}"
)

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric("ROE", f"{roe}%")

with k2:
    st.metric("ROCE", f"{roce}%")

with k3:
    st.metric("Net Profit Margin", f"{npm}%")

with k4:
    st.metric("Debt / Equity", de)

with k5:
    st.metric("Revenue CAGR 5Y", f"{revenue_cagr}%")

with k6:
    st.metric("Free Cash Flow", f"{fcf} Cr")

# ---------------------------------------------------------
# REVENUE + NET PROFIT CHART
# ---------------------------------------------------------

st.markdown("### Revenue & Net Profit — 10 Year Trend")

if not pl.empty:

    chart_data = pl[
        ["year", "sales", "net_profit"]
    ].copy()

    chart_data["sales"] = pd.to_numeric(
        chart_data["sales"],
        errors="coerce"
    )

    chart_data["net_profit"] = pd.to_numeric(
        chart_data["net_profit"],
        errors="coerce"
    )

    chart_data = chart_data.tail(10)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=chart_data["year"],
            y=chart_data["sales"],
            name="Revenue"
        )
    )

    fig.add_trace(
        go.Bar(
            x=chart_data["year"],
            y=chart_data["net_profit"],
            name="Net Profit"
        )
    )

    fig.update_layout(
        barmode="group",
        height=500,
        xaxis_title="Year",
        yaxis_title="Amount (₹ Cr)"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:
    st.info("Financial data not available.")

# ---------------------------------------------------------
# ROE + ROCE CHART
# ---------------------------------------------------------

st.markdown("### ROE & ROCE — 10 Year Trend")

if not ratios.empty:

    roe_chart = ratios[
        ["year", "return_on_equity_pct"]
    ].copy()

    roe_chart["ROE"] = pd.to_numeric(
        roe_chart["return_on_equity_pct"],
        errors="coerce"
    )

    # Calculate ROCE for every available year
    roce_rows = []

    for year in ratios["year"].unique():

        pl_year = pl[
            pl["year"] == year
        ]

        bs_year = bs[
            bs["year"] == year
        ]

        if not pl_year.empty and not bs_year.empty:

            op = pd.to_numeric(
                pl_year.iloc[0]["operating_profit"],
                errors="coerce"
            )

            equity = pd.to_numeric(
                bs_year.iloc[0]["total_equity"],
                errors="coerce"
            )

            debt = pd.to_numeric(
                bs_year.iloc[0]["debt"],
                errors="coerce"
            )

            if (
                pd.notna(op)
                and pd.notna(equity)
                and pd.notna(debt)
                and equity + debt != 0
            ):
                roce_value = (
                    op / (equity + debt) * 100
                )
            else:
                roce_value = None

        else:
            roce_value = None

        roce_rows.append(
            {
                "year": year,
                "ROCE": roce_value
            }
        )

    roce_chart = pd.DataFrame(roce_rows)

    performance = roe_chart[
        ["year", "ROE"]
    ].merge(
        roce_chart,
        on="year",
        how="left"
    )

    performance = performance.tail(10)

    fig2 = go.Figure()

    fig2.add_trace(
        go.Scatter(
            x=performance["year"],
            y=performance["ROE"],
            mode="lines+markers",
            name="ROE"
        )
    )

    fig2.add_trace(
        go.Scatter(
            x=performance["year"],
            y=performance["ROCE"],
            mode="lines+markers",
            name="ROCE"
        )
    )

    fig2.update_layout(
        height=500,
        xaxis_title="Year",
        yaxis_title="Percentage (%)"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

else:
    st.info("Ratio data not available.")

# ---------------------------------------------------------
# PROS & CONS
# ---------------------------------------------------------

st.markdown("### Pros & Cons")

pros_col, cons_col = st.columns(2)

with pros_col:
    st.markdown("#### ✅ Pros")
    st.info(
        "Pros data is not available in the current dataset."
    )

with cons_col:
    st.markdown("#### ❌ Cons")
    st.info(
        "Cons data is not available in the current dataset."
    )

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown("---")

st.caption(
    f"Nifty 100 Analytics • {company_name} • "
    f"Latest available year: {latest_year}"
)