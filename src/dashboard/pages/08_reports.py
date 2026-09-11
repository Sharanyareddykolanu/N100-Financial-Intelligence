import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"

st.title("Annual Reports")
st.caption("Find available annual reports for Nifty 100 companies")


def read_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


companies = read_query(
    """
    SELECT company_id, company_name, ticker
    FROM companies
    ORDER BY company_name
    """
)

if companies.empty:
    st.warning("No company data available.")
    st.stop()


companies["display"] = (
    companies["company_name"]
    + " ("
    + companies["ticker"].fillna(companies["company_id"])
    + ")"
)

selected = st.selectbox(
    "Search / Select Company",
    companies["display"].tolist()
)

company_id = companies.loc[
    companies["display"] == selected,
    "company_id"
].iloc[0]

company_name = companies.loc[
    companies["company_id"] == company_id,
    "company_name"
].iloc[0]

ticker = companies.loc[
    companies["company_id"] == company_id,
    "ticker"
].iloc[0]


st.markdown(f"### {company_name} ({ticker})")

# Check documents table
try:
    reports = read_query(
        """
        SELECT *
        FROM documents
        WHERE company_id = ?
        """,
        (company_id,)
    )
except Exception:
    reports = pd.DataFrame()


if reports.empty:
    st.info(
        "Annual report records are not available in the current database."
    )

    st.markdown(
        "### Report Status"
    )

    st.warning(
        "No annual report links were found for this company."
    )

else:
    st.markdown("### Available Annual Reports")

    # Try to identify year and URL columns
    year_column = None
    url_column = None

    for column in reports.columns:
        name = column.lower()

        if year_column is None and "year" in name:
            year_column = column

        if url_column is None and (
            "url" in name
            or "link" in name
            or "pdf" in name
        ):
            url_column = column

    if year_column is None:
        st.dataframe(
            reports,
            use_container_width=True,
            hide_index=True
        )
    else:

        reports = reports.sort_values(
            year_column,
            ascending=False
        )

        for _, row in reports.iterrows():

            year = row[year_column]

            if url_column is not None:
                url = row[url_column]

                if pd.notna(url) and str(url).strip():
                    st.markdown(
                        f"**{year}** — "
                        f"[View Annual Report]({url})"
                    )
                else:
                    st.error(
                        f"🔴 {year} — Report unavailable"
                    )

            else:
                st.error(
                    f"🔴 {year} — Report unavailable"
                )