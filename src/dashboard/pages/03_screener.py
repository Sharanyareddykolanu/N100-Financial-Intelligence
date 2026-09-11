import sys
from pathlib import Path
import sqlite3

import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# PYTHON PATH
# ---------------------------------------------------------

SRC_PATH = Path(__file__).resolve().parents[2]

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from screener.presets import PRESETS


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"


@st.cache_data(ttl=600)
def load_screener_data():
    query = """
        SELECT
            fr.*,
            pl.sales,
            pl.net_profit,
            cv.market_cap,
            cv.pe_ratio,
            cv.pb_ratio,
            cv.dividend_yield,
            c.company_name,
            c.ticker,
            c.sector
        FROM financial_ratios fr

        LEFT JOIN company_profit_loss pl
            ON fr.company_id = pl.company_id
            AND fr.year = pl.year

        LEFT JOIN company_valuation cv
            ON fr.company_id = cv.company_id
            AND fr.year = cv.year

        LEFT JOIN companies c
            ON fr.company_id = c.company_id
    """

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


# ---------------------------------------------------------
# PAGE TITLE
# ---------------------------------------------------------

st.title("Nifty 100 Screener")
st.write(
    "Filter companies using fundamental and valuation metrics."
)


data = load_screener_data()

if data.empty:
    st.warning("No screener data available.")
    st.stop()


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

defaults = {
    "roe_min": 15.0,
    "de_max": 1.0,
    "fcf_min": 0.0,
    "revenue_cagr_min": 10.0,
    "pat_cagr_min": 10.0,
    "opm_min": 10.0,
    "pe_max": 30.0,
    "pb_max": 5.0,
    "dividend_yield_min": 1.0,
    "icr_min": 3.0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------
# PRESET FUNCTIONS
# ---------------------------------------------------------

preset_values = {
    "Quality": {
        "roe_min": 15.0,
        "de_max": 1.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 10.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 10.0,
        "dividend_yield_min": 0.0,
        "icr_min": 0.0,
    },

    "Value": {
        "roe_min": 0.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 20.0,
        "pb_max": 3.0,
        "dividend_yield_min": 1.0,
        "icr_min": 0.0,
    },

    "Growth": {
        "roe_min": 0.0,
        "de_max": 2.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 15.0,
        "pat_cagr_min": 20.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 10.0,
        "dividend_yield_min": 0.0,
        "icr_min": 0.0,
    },

    "Dividend": {
        "roe_min": 0.0,
        "de_max": 10.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 10.0,
        "dividend_yield_min": 2.0,
        "icr_min": 0.0,
    },

    "Debt-Free": {
        "roe_min": 12.0,
        "de_max": 0.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 0.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 10.0,
        "dividend_yield_min": 0.0,
        "icr_min": 0.0,
    },

    "Turnaround": {
        "roe_min": 0.0,
        "de_max": 10.0,
        "fcf_min": 0.0,
        "revenue_cagr_min": 10.0,
        "pat_cagr_min": 0.0,
        "opm_min": 0.0,
        "pe_max": 100.0,
        "pb_max": 10.0,
        "dividend_yield_min": 0.0,
        "icr_min": 0.0,
    },
}


def apply_preset(name):
    values = preset_values[name]

    for key, value in values.items():
        st.session_state[key] = value


# ---------------------------------------------------------
# PRESET BUTTONS
# ---------------------------------------------------------

st.sidebar.markdown("## Presets")

preset_cols = st.sidebar.columns(2)

preset_names = [
    "Quality",
    "Value",
    "Growth",
    "Dividend",
    "Debt-Free",
    "Turnaround",
]

for index, preset_name in enumerate(preset_names):

    with preset_cols[index % 2]:

        if st.button(
            preset_name,
            use_container_width=True,
            key=f"preset_{preset_name}"
        ):
            apply_preset(preset_name)
            st.rerun()


# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------

st.sidebar.markdown("## Filters")

st.sidebar.slider(
    "ROE minimum (%)",
    min_value=0.0,
    max_value=100.0,
    step=1.0,
    key="roe_min"
)

st.sidebar.slider(
    "D/E maximum",
    min_value=0.0,
    max_value=10.0,
    step=0.1,
    key="de_max"
)

st.sidebar.slider(
    "FCF minimum (₹ Cr)",
    min_value=0.0,
    max_value=100000.0,
    step=100.0,
    key="fcf_min"
)

st.sidebar.slider(
    "Revenue CAGR minimum (%)",
    min_value=0.0,
    max_value=100.0,
    step=1.0,
    key="revenue_cagr_min"
)

st.sidebar.slider(
    "PAT CAGR minimum (%)",
    min_value=0.0,
    max_value=100.0,
    step=1.0,
    key="pat_cagr_min"
)

st.sidebar.slider(
    "OPM minimum (%)",
    min_value=0.0,
    max_value=100.0,
    step=1.0,
    key="opm_min"
)

st.sidebar.slider(
    "P/E maximum",
    min_value=1.0,
    max_value=200.0,
    step=1.0,
    key="pe_max"
)

st.sidebar.slider(
    "P/B maximum",
    min_value=0.0,
    max_value=50.0,
    step=0.5,
    key="pb_max"
)

st.sidebar.slider(
    "Dividend Yield minimum (%)",
    min_value=0.0,
    max_value=20.0,
    step=0.5,
    key="dividend_yield_min"
)

st.sidebar.slider(
    "ICR minimum",
    min_value=0.0,
    max_value=50.0,
    step=1.0,
    key="icr_min"
)


# ---------------------------------------------------------
# APPLY FILTERS
# ---------------------------------------------------------

result = data.copy()

# ROE
result = result[
    result["return_on_equity_pct"].notna()
    & (
        result["return_on_equity_pct"]
        >= st.session_state.roe_min
    )
]

# D/E
de_values = pd.to_numeric(
    result["debt_to_equity"],
    errors="coerce"
)

result = result[
    de_values.notna()
    & (
        de_values
        <= st.session_state.de_max
    )
]

# FCF
result = result[
    result["free_cash_flow_cr"].notna()
    & (
        result["free_cash_flow_cr"]
        >= st.session_state.fcf_min
    )
]

# Revenue CAGR
result = result[
    result["revenue_cagr_5yr"].notna()
    & (
        result["revenue_cagr_5yr"]
        >= st.session_state.revenue_cagr_min
    )
]

# PAT CAGR
result = result[
    result["pat_cagr_5yr"].notna()
    & (
        result["pat_cagr_5yr"]
        >= st.session_state.pat_cagr_min
    )
]

# OPM
result = result[
    result["operating_profit_margin_pct"].notna()
    & (
        result["operating_profit_margin_pct"]
        >= st.session_state.opm_min
    )
]

# P/E
result = result[
    result["pe_ratio"].notna()
    & (
        result["pe_ratio"]
        <= st.session_state.pe_max
    )
]

# P/B
result = result[
    result["pb_ratio"].notna()
    & (
        result["pb_ratio"]
        <= st.session_state.pb_max
    )
]

# Dividend Yield
result = result[
    result["dividend_yield"].notna()
    & (
        result["dividend_yield"]
        >= st.session_state.dividend_yield_min
    )
]

# ICR
icr = result["interest_coverage"].copy()

# NULL ICR = debt-free = infinity
icr = icr.fillna(float("inf"))

result = result[
    icr >= st.session_state.icr_min
]


# ---------------------------------------------------------
# SORT
# ---------------------------------------------------------

result = result.sort_values(
    "composite_quality_score",
    ascending=False,
    na_position="last"
)


# ---------------------------------------------------------
# RESULT COUNT
# ---------------------------------------------------------

st.subheader(
    f"{len(result)} companies match your filters"
)


# ---------------------------------------------------------
# DISPLAY TABLE
# ---------------------------------------------------------

display_columns = [
    "company_id",
    "company_name",
    "ticker",
    "sector",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield",
    "interest_coverage",
    "composite_quality_score",
]

available_columns = [
    column
    for column in display_columns
    if column in result.columns
]

visible_result = result[available_columns].copy()

st.dataframe(
    visible_result,
    use_container_width=True,
    hide_index=True
)


# ---------------------------------------------------------
# CSV DOWNLOAD
# ---------------------------------------------------------

csv_data = visible_result.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Results as CSV",
    data=csv_data,
    file_name="nifty100_screener_results.csv",
    mime="text/csv",
)