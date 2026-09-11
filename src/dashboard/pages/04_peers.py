
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


st.title("Peer Comparison")
st.caption("Compare companies against their peer group")


# ---------------------------------------------------------
# Database helpers
# ---------------------------------------------------------

def read_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params=params
        )

    if "year" in df.columns:
        def convert_year(value):
            if isinstance(value, (bytes, bytearray)):
                return int.from_bytes(value, "little")
            return pd.to_numeric(
                value,
                errors="coerce"
            )

        df["year"] = df["year"].apply(convert_year)

    return df


# ---------------------------------------------------------
# Peer groups
# ---------------------------------------------------------

peer_groups = read_query(
    """
    SELECT DISTINCT peer_group_name
    FROM peer_percentiles
    ORDER BY peer_group_name
    """
)

if peer_groups.empty:
    st.error("No peer group data found.")
    st.stop()

groups = peer_groups["peer_group_name"].tolist()

selected_group = st.selectbox(
    "Select Peer Group",
    groups
)


# ---------------------------------------------------------
# Load peer data
# ---------------------------------------------------------

peer_data = read_query(
    """
    SELECT
        pp.company_id,
        pp.peer_group_name,
        pp.metric,
        pp.value,
        pp.percentile_rank,
        pp.year,
        c.company_name,
        c.ticker
    FROM peer_percentiles pp
    LEFT JOIN companies c
        ON pp.company_id = c.company_id
    WHERE pp.peer_group_name = ?
    ORDER BY pp.company_id, pp.year, pp.metric
    """,
    (selected_group,)
)

if peer_data.empty:
    st.warning("No data available for this peer group.")
    st.stop()


# ---------------------------------------------------------
# Year selector
# ---------------------------------------------------------

years = sorted(
    pd.to_numeric(
        peer_data["year"],
        errors="coerce"
    ).dropna().unique().tolist()
)

if not years:
    st.warning("No year information available.")
    st.stop()

selected_year = st.selectbox(
    "Select Year",
    years,
    index=len(years) - 1
)

year_data = peer_data[
    pd.to_numeric(peer_data["year"], errors="coerce")
    == selected_year
].copy()

if year_data.empty:
    st.warning("No data available for the selected year.")
    st.stop()


# ---------------------------------------------------------
# Companies in selected peer group
# ---------------------------------------------------------

company_options = (
    year_data[
        ["company_id", "company_name", "ticker"]
    ]
    .drop_duplicates()
    .sort_values("company_name")
)

company_options["display"] = (
    company_options["company_name"].fillna("")
    + " ("
    + company_options["ticker"].fillna(
        company_options["company_id"]
    )
    + ")"
)

selected_display = st.selectbox(
    "Select Company",
    company_options["display"].tolist()
)

selected_company = company_options.loc[
    company_options["display"] == selected_display,
    "company_id"
].iloc[0]


# ---------------------------------------------------------
# Benchmark mapping
# ---------------------------------------------------------

benchmark_map = {
    "Private Banks": "HDFCBANK",
    "Public Sector Banks": "SBIN",
    "IT Services": "TCS",
    "Pharmaceuticals": "SUNPHARMA",
    "Automobiles": "MARUTI",
    "Life Insurance": "LICI",
    "Oil & Gas": "RELIANCE",
    "Power & Utilities": "NTPC",
    "Steel": "TATASTEEL",
    "FMCG": "HINDUNILVR",
    "Consumer Finance": "BAJFINANCE",
}

benchmark_company = benchmark_map.get(
    selected_group
)


# ---------------------------------------------------------
# Company information
# ---------------------------------------------------------

selected_info = company_options[
    company_options["company_id"] == selected_company
].iloc[0]

benchmark_info = company_options[
    company_options["company_id"] == benchmark_company
]

benchmark_name = benchmark_company

if not benchmark_info.empty:
    benchmark_name = benchmark_info.iloc[0]["company_name"]


st.markdown("### Selected Company")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Company",
        selected_info["company_name"]
    )

with col2:
    st.metric(
        "Peer Group",
        selected_group
    )

with col3:
    st.metric(
        "Benchmark",
        benchmark_name
    )


# ---------------------------------------------------------
# Radar chart
# ---------------------------------------------------------

st.markdown("### Performance vs Peer Average")

radar_metrics = [
    "ROE",
    "ROCE",
    "Net Profit Margin",
    "D/E",
    "FCF",
    "PAT CAGR 5yr",
    "Revenue CAGR 5yr",
    "EPS CAGR 5yr",
]

radar_data = year_data[
    year_data["metric"].isin(radar_metrics)
].copy()

selected_radar = radar_data[
    radar_data["company_id"] == selected_company
].copy()

peer_average = (
    radar_data
    .groupby("metric")["value"]
    .mean()
    .to_dict()
)

selected_values = []

for metric in radar_metrics:
    row = selected_radar[
        selected_radar["metric"] == metric
    ]

    if row.empty:
        selected_values.append(0)
    else:
        selected_values.append(
            float(row.iloc[0]["value"])
        )

average_values = [
    float(peer_average.get(metric, 0))
    for metric in radar_metrics
]


# Close radar polygons
theta = radar_metrics + [radar_metrics[0]]
company_radar = selected_values + [selected_values[0]]
average_radar = average_values + [average_values[0]]

fig = go.Figure()

fig.add_trace(
    go.Scatterpolar(
        r=company_radar,
        theta=theta,
        fill="toself",
        name=selected_info["ticker"],
    )
)

fig.add_trace(
    go.Scatterpolar(
        r=average_radar,
        theta=theta,
        fill="toself",
        name="Peer Average",
    )
)

fig.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True
        )
    ),
    height=600,
    title=f"{selected_info['ticker']} vs {selected_group} Average",
    showlegend=True,
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ---------------------------------------------------------
# Side-by-side KPI table
# ---------------------------------------------------------

st.markdown("### Peer Group Comparison")

table_data = year_data[
    year_data["metric"].isin(radar_metrics)
].pivot_table(
    index=["company_id", "company_name", "ticker"],
    columns="metric",
    values="value",
    aggfunc="first"
).reset_index()


# Keep columns in requested order
available_metrics = [
    metric
    for metric in radar_metrics
    if metric in table_data.columns
]

table_columns = [
    "company_id",
    "company_name",
    "ticker",
] + available_metrics

table_data = table_data[
    [col for col in table_columns if col in table_data.columns]
].copy()


# Round numeric values
for column in table_data.columns:
    if column not in [
        "company_id",
        "company_name",
        "ticker",
    ]:
        table_data[column] = pd.to_numeric(
            table_data[column],
            errors="coerce"
        ).round(2)


# ---------------------------------------------------------
# Highlight benchmark company
# ---------------------------------------------------------

def highlight_benchmark(row):
    if row["company_id"] == benchmark_company:
        return [
            "background-color: #fff3cd; font-weight: bold"
            for _ in row
        ]

    return [""] * len(row)


st.dataframe(
    table_data.style.apply(
        highlight_benchmark,
        axis=1
    ),
    use_container_width=True,
    hide_index=True
)

st.caption(
    f"Benchmark company: {benchmark_company} "
    f"• Selected year: {selected_year}"
)

