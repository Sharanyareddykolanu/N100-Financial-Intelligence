import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# Project root: D:\N100-Financial-Intelligence
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "nifty100.db"


def _read_query(query, params=()):
    """Run a read-only SQLite query and return a DataFrame."""
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_companies():
    return _read_query(
        """
        SELECT *
        FROM companies
        ORDER BY company_id
        """
    )


@st.cache_data(ttl=600)
def get_ratios(ticker, year=None):
    if year is None:
        return _read_query(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year
            """,
            (ticker,),
        )

    return _read_query(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
          AND year = ?
        ORDER BY year
        """,
        (ticker, year),
    )


@st.cache_data(ttl=600)
def get_pl(ticker):
    return _read_query(
        """
        SELECT *
        FROM company_profit_loss
        WHERE company_id = ?
        ORDER BY year
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_bs(ticker):
    return _read_query(
        """
        SELECT *
        FROM company_balance_sheet
        WHERE company_id = ?
        ORDER BY year
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_cf(ticker):
    return _read_query(
        """
        SELECT *
        FROM company_cashflow
        WHERE company_id = ?
        ORDER BY year
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_sectors():
    return _read_query(
        """
        SELECT *
        FROM company_sector
        ORDER BY company_id
        """
    )


@st.cache_data(ttl=600)
def get_peers(group_name):
    return _read_query(
        """
        SELECT *
        FROM peer_percentiles
        WHERE peer_group_name = ?
        ORDER BY company_id, year, metric
        """,
        (group_name,),
    )


@st.cache_data(ttl=600)
def get_valuation(ticker):
    return _read_query(
        """
        SELECT *
        FROM company_valuation
        WHERE company_id = ?
        ORDER BY year
        """,
        (ticker,),
    )