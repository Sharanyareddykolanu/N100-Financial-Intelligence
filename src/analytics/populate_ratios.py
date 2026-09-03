"""
Day 12 - Populate financial_ratios table

Populates all available financial KPIs for all company/year records.
"""

import sqlite3
from pathlib import Path

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    debt_to_equity,
    interest_coverage_ratio,
    asset_turnover,
)

from src.analytics.cagr import compute_window_cagr
from src.analytics.cashflow import (
    free_cash_flow,
)


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = BASE_DIR / "nifty100.db"


def _safe_divide(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _get_cagr(conn, company_id, column, years):
    rows = conn.execute(
        f"""
        SELECT year, {column}
        FROM company_financials
        WHERE company_id = ?
          AND {column} IS NOT NULL
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    values = [row[1] for row in rows]

    value, flag = compute_window_cagr(values, years)

    return value


def _get_pat_cagr(conn, company_id, years):
    rows = conn.execute(
        """
        SELECT year, net_profit
        FROM company_profit_loss
        WHERE company_id = ?
          AND net_profit IS NOT NULL
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    values = [row[1] for row in rows]

    value, flag = compute_window_cagr(values, years)

    return value


def _get_eps_cagr(conn, company_id, years):
    rows = conn.execute(
        """
        SELECT year, eps
        FROM company_profit_loss
        WHERE company_id = ?
          AND eps IS NOT NULL
        ORDER BY year
        """,
        (company_id,),
    ).fetchall()

    values = [row[1] for row in rows]

    value, flag = compute_window_cagr(values, years)

    return value


def _composite_quality_score(
    npm,
    opm,
    roe,
    debt_equity,
    icr,
    asset_turnover_value,
    fcf,
    revenue_cagr,
):
    """
    Simple 8-factor quality score.

    Each positive/healthy factor contributes 12.5 points.
    Maximum = 100.
    """

    score = 0.0
    factors = 0

    checks = [
        npm is not None and npm > 0,
        opm is not None and opm > 0,
        roe is not None and roe > 0,
        debt_equity is not None and debt_equity <= 1,
        icr is not None and icr >= 3,
        asset_turnover_value is not None and asset_turnover_value >= 1,
        fcf is not None and fcf > 0,
        revenue_cagr is not None and revenue_cagr > 0,
    ]

    for result in checks:
        factors += 1
        if result:
            score += 12.5

    if factors == 0:
        return None

    return score


def populate_financial_ratios(db_path=DEFAULT_DB):
    conn = sqlite3.connect(db_path)

    conn.execute("DELETE FROM financial_ratios")

    rows = conn.execute(
        """
        SELECT
            p.company_id,
            p.year,
            p.sales,
            p.operating_profit,
            p.net_profit,
            p.eps,

            b.total_assets,
            b.total_equity,
            b.debt,

            f.revenue,
            f.dividend,

            c.operating_cash_flow,
            c.investing_cash_flow,
            c.free_cash_flow

        FROM company_profit_loss p

        LEFT JOIN company_balance_sheet b
            ON p.company_id = b.company_id
           AND p.year = b.year

        LEFT JOIN company_financials f
            ON p.company_id = f.company_id
           AND p.year = f.year

        LEFT JOIN company_cashflow c
            ON p.company_id = c.company_id
           AND p.year = c.year

        ORDER BY p.company_id, p.year
        """
    ).fetchall()

    insert_rows = []

    for row in rows:

        (
            company_id,
            year,
            sales,
            operating_profit,
            net_profit,
            eps,
            total_assets,
            total_equity,
            debt,
            revenue,
            dividend,
            cfo,
            cfi,
            stored_fcf,
        ) = row

        # ----------------------------------------------------
        # Profitability
        # ----------------------------------------------------

        npm = net_profit_margin(
            net_profit,
            sales,
        )

        opm = operating_profit_margin(
            operating_profit,
            sales,
        )

        roe = return_on_equity(
            net_profit,
            total_equity,
            0,
        )

        # ----------------------------------------------------
        # Leverage / efficiency
        # ----------------------------------------------------

        de = debt_to_equity(
            debt,
            total_equity,
            0,
        )

        # Interest data is not present in the current schema.
        icr = None

        turnover = asset_turnover(
            sales,
            total_assets,
        )

        # ----------------------------------------------------
        # Cash flow
        # ----------------------------------------------------

        if stored_fcf is not None:
            fcf = stored_fcf
        elif cfo is not None and cfi is not None:
            fcf = free_cash_flow(
                cfo,
                cfi,
            )
        else:
            fcf = None

        capex = abs(cfi) if cfi is not None else None

        # ----------------------------------------------------
        # Per-share metrics
        # ----------------------------------------------------

        earnings_per_share = eps

        # Shares outstanding are not available.
        book_value_per_share = None

        # ----------------------------------------------------
        # Dividend payout
        # ----------------------------------------------------

       	dividend_payout = None
        # ----------------------------------------------------
        # 5-year CAGR
        # ----------------------------------------------------

        revenue_cagr = _get_cagr(
            conn,
            company_id,
            "revenue",
            5,
        )

        pat_cagr = _get_pat_cagr(
            conn,
            company_id,
            5,
        )

        eps_cagr = _get_eps_cagr(
            conn,
            company_id,
            5,
        )

        # ----------------------------------------------------
        # Composite quality score
        # ----------------------------------------------------

        quality_score = _composite_quality_score(
            npm,
            opm,
            roe,
            de,
            icr,
            turnover,
            fcf,
            revenue_cagr,
        )

        insert_rows.append(
            (
                company_id,
                year,
                npm,
                opm,
                roe,
                de,
                icr,
                turnover,
                fcf,
                capex,
                earnings_per_share,
                book_value_per_share,
                dividend_payout,
                debt,
                cfo,
                revenue_cagr,
                pat_cagr,
                eps_cagr,
                quality_score,
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO financial_ratios (
            company_id,
            year,
            net_profit_margin_pct,
            operating_profit_margin_pct,
            return_on_equity_pct,
            debt_to_equity,
            interest_coverage,
            asset_turnover,
            free_cash_flow_cr,
            capex_cr,
            earnings_per_share,
            book_value_per_share,
            dividend_payout_ratio_pct,
            total_debt_cr,
            cash_from_operations_cr,
            revenue_cagr_5yr,
            pat_cagr_5yr,
            eps_cagr_5yr,
            composite_quality_score
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        insert_rows,
    )

    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    conn.close()

    return count


if __name__ == "__main__":
    count = populate_financial_ratios()

    print(
        f"financial_ratios rows populated: {count}"
    )

    if count >= 1100:
        print("PASS: row count requirement >= 1100")
    else:
        print("FAIL: row count requirement not met")