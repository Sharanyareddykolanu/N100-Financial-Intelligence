import sys
from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st
import plotly.graph_objects as go


SRC_PATH = Path(__file__).resolve().parents[2]

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"


st.title("Trend Analysis")
st.caption("Analyze long-term financial trends for a selected company")


def read_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            query,
            conn,
            params=params
        )


# ---------------------------------------------------------
# Company Selection
# ---------------------------------------------------------

companies = read_query(
    """
    SELECT company_id, company_name, ticker
    FROM companies
    ORDER BY company_name
    """
)

if companies.empty:
    st.error("No company data available.")
    st.stop()


companies["display"] = (
    companies["company_name"].fillna("")
    + " ("
    + companies["ticker"].fillna(companies["company_id"])
    + ")"
)


selected_display = st.selectbox(
    "Search / Select Company",
    companies["display"].tolist()
)


selected_company = companies.loc[
    companies["display"] == selected_display,
    "company_id"
].iloc[0]


selected_company_name = companies.loc[
    companies["company_id"] == selected_company,
    "company_name"
].iloc[0]


selected_ticker = companies.loc[
    companies["company_id"] == selected_company,
    "ticker"
].iloc[0]


# ---------------------------------------------------------
# Load Financial Ratio Data
# ---------------------------------------------------------

data = read_query(
    """
    SELECT
        company_id,
        year,
        return_on_equity_pct,
        operating_profit_margin_pct,
        net_profit_margin_pct,
        debt_to_equity,
        free_cash_flow_cr,
        revenue_cagr_5yr,
        pat_cagr_5yr,
        eps_cagr_5yr,
        asset_turnover
    FROM financial_ratios
    WHERE company_id = ?
    ORDER BY year
    """,
    (selected_company,)
)


if data.empty:
    st.warning(
        f"No financial trend data available for {selected_ticker}."
    )
    st.stop()


data["year"] = pd.to_numeric(
    data["year"],
    errors="coerce"
)

data = data.dropna(
    subset=["year"]
).copy()

data["year"] = data["year"].astype(int)


# ---------------------------------------------------------
# Metric Selection
# ---------------------------------------------------------

metric_map = {
    "ROE (%)": "return_on_equity_pct",
    "Operating Profit Margin (%)": "operating_profit_margin_pct",
    "Net Profit Margin (%)": "net_profit_margin_pct",
    "Debt to Equity": "debt_to_equity",
    "Free Cash Flow (Cr)": "free_cash_flow_cr",
    "Revenue CAGR 5Y (%)": "revenue_cagr_5yr",
    "PAT CAGR 5Y (%)": "pat_cagr_5yr",
    "EPS CAGR 5Y (%)": "eps_cagr_5yr",
    "Asset Turnover": "asset_turnover",
}


selected_metrics = st.multiselect(
    "Select up to 3 Metrics",
    list(metric_map.keys()),
    default=["ROE (%)"],
    max_selections=3
)


if not selected_metrics:
    st.info("Select at least one metric to display the trend.")
    st.stop()


# ---------------------------------------------------------
# Trend Chart
# ---------------------------------------------------------

st.markdown(
    f"### {selected_company_name} ({selected_ticker}) — 10-Year Trend"
)


fig = go.Figure()


for metric_label in selected_metrics:

    column = metric_map[metric_label]

    metric_data = data[
        ["year", column]
    ].copy()

    metric_data[column] = pd.to_numeric(
        metric_data[column],
        errors="coerce"
    )

    metric_data = metric_data.dropna(
        subset=[column]
    ).sort_values("year")

    if metric_data.empty:
        continue

    metric_data["yoy_change"] = (
        metric_data[column]
        .pct_change()
        .replace(
            [float("inf"), -float("inf")],
            pd.NA
        )
        * 100
    )

    customdata = []

    for _, row in metric_data.iterrows():

        yoy = row["yoy_change"]

        if pd.isna(yoy):
            yoy_text = "N/A"
        else:
            yoy_text = f"{yoy:+.2f}%"

        customdata.append(
            [yoy_text]
        )

    fig.add_trace(
        go.Scatter(
            x=metric_data["year"],
            y=metric_data[column],
            mode="lines+markers",
            name=metric_label,
            customdata=customdata,
            hovertemplate=(
                "<b>Year:</b> %{x}"
                "<br><b>Value:</b> %{y:.2f}"
                "<br><b>YoY Change:</b> %{customdata[0]}"
                "<extra></extra>"
            )
        )
    )


fig.update_layout(
    height=550,
    hovermode="x unified",
    xaxis_title="Year",
    yaxis_title="Metric Value",
    legend_title="Metrics",
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20
    )
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ---------------------------------------------------------
# YoY Change Table
# ---------------------------------------------------------

st.markdown("### Year-on-Year Change")


yoy_table = data[
    ["year"]
].copy()


for metric_label in selected_metrics:

    column = metric_map[metric_label]

    values = pd.to_numeric(
        data[column],
        errors="coerce"
    )

    yoy_values = (
        values
        .pct_change()
        .replace(
            [float("inf"), -float("inf")],
            pd.NA
        )
        * 100
    )

    yoy_table[metric_label] = yoy_values.round(2)


yoy_table = yoy_table.sort_values(
    "year",
    ascending=False
)


st.dataframe(
    yoy_table,
    use_container_width=True,
    hide_index=True
)


# ---------------------------------------------------------
# Data Availability Note
# ---------------------------------------------------------

available_years = sorted(
    data["year"].unique().tolist()
)

if available_years:

    st.info(
        f"Data available from {available_years[0]} "
        f"to {available_years[-1]}. "
        f"Some metrics may have missing values for individual years."
    )