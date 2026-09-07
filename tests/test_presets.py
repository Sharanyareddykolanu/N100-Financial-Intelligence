import sqlite3

import pandas as pd

from src.screener.presets import PRESETS


def load_data():
    conn = sqlite3.connect("nifty100.db")

    query = """
    SELECT
        fr.*,
        pl.sales,
        pl.net_profit,
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

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def test_all_six_presets_exist():
    assert len(PRESETS) == 6

    expected = {
        "Quality Compounder",
        "Value Pick",
        "Growth Accelerator",
        "Dividend Champion",
        "Debt-Free Blue Chip",
        "Turnaround Watch",
    }

    assert set(PRESETS.keys()) == expected


def test_quality_compounder_range():
    df = load_data()
    result = PRESETS["Quality Compounder"](df)

    assert 5 <= result["company_id"].nunique() <= 50


def test_value_pick_range():
    df = load_data()
    result = PRESETS["Value Pick"](df)

    assert 5 <= result["company_id"].nunique() <= 50


def test_growth_accelerator_range():
    df = load_data()
    result = PRESETS["Growth Accelerator"](df)

    assert 5 <= result["company_id"].nunique() <= 50


def test_debt_free_blue_chip_range():
    df = load_data()
    result = PRESETS["Debt-Free Blue Chip"](df)

    assert 5 <= result["company_id"].nunique() <= 50


def test_turnaround_watch_range():
    df = load_data()
    result = PRESETS["Turnaround Watch"](df)

    assert 5 <= result["company_id"].nunique() <= 50


def test_dividend_champion_requires_payout_data():
    df = load_data()

    result = PRESETS["Dividend Champion"](df)

    payout_available = df["dividend_payout_ratio_pct"].notna().any()

    if not payout_available:
        assert len(result) == 0