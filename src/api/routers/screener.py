from pathlib import Path
import sqlite3

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/screener", tags=["Screener"])

# Project root: D:\N100-Financial-Intelligence
ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def screener(
    min_roe: float | None = Query(default=None, ge=-10000, le=10000),
    max_de: float | None = Query(default=None, ge=0, le=1000),
    min_fcf: float | None = Query(default=None),
    sector: str | None = Query(default=None, min_length=1),
    min_rev_cagr_5yr: float | None = Query(default=None, ge=-1000, le=1000),
    min_pat_cagr_5yr: float | None = Query(default=None, ge=-1000, le=1000),
    max_pe: float | None = Query(default=None, gt=0, le=10000),
):
    """
    Dynamic Nifty100 company screener.

    Supported filters:
    - min_roe
    - max_de
    - min_fcf
    - sector
    - min_rev_cagr_5yr
    - min_pat_cagr_5yr
    - max_pe

    Results are ranked by composite_quality_score descending.
    """

    # Extra validation for values that FastAPI constraints alone don't catch.
    if max_de is not None and max_de < 0:
        raise HTTPException(
            status_code=400,
            detail="max_de must be greater than or equal to 0",
        )

    if max_pe is not None and max_pe <= 0:
        raise HTTPException(
            status_code=400,
            detail="max_pe must be greater than 0",
        )

    if sector is not None and not sector.strip():
        raise HTTPException(
            status_code=400,
            detail="sector cannot be empty",
        )

    conn = get_connection()

    try:
        # The API uses the exact 92-company universe from company_sector.
        query = """
            WITH latest_ratios AS (
                SELECT
                    fr.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY fr.company_id
                        ORDER BY fr.year DESC
                    ) AS rn
                FROM financial_ratios fr
            ),
            latest_valuation AS (
                SELECT
                    cv.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY cv.company_id
                        ORDER BY cv.year DESC
                    ) AS rn
                FROM company_valuation cv
            )
            SELECT
                c.company_id,
                c.company_name,
                c.ticker,
                cs.sector,
                lr.year,

                lr.return_on_equity_pct,
                lr.operating_profit_margin_pct,
                lr.net_profit_margin_pct,
                lr.free_cash_flow_cr,
                lr.revenue_cagr_5yr,
                lr.pat_cagr_5yr,
                lr.eps_cagr_5yr,
                lr.debt_to_equity,
                lr.interest_coverage,
                lr.asset_turnover,
                lr.composite_quality_score,

                lv.market_cap,
                lv.pe_ratio,
                lv.pb_ratio,
                lv.dividend_yield

            FROM companies c

            INNER JOIN company_sector cs
                ON cs.company_id = c.company_id

            LEFT JOIN latest_ratios lr
                ON lr.company_id = c.company_id
                AND lr.rn = 1

            LEFT JOIN latest_valuation lv
                ON lv.company_id = c.company_id
                AND lv.rn = 1

            WHERE 1 = 1
        """

        params = []

        # -----------------------------
        # Dynamic filters
        # -----------------------------

        if min_roe is not None:
            query += """
                AND lr.return_on_equity_pct >= ?
            """
            params.append(min_roe)

        if max_de is not None:
            query += """
                AND (
                    lr.debt_to_equity IS NULL
                    OR lr.debt_to_equity <= ?
                )
            """
            params.append(max_de)

        if min_fcf is not None:
            query += """
                AND lr.free_cash_flow_cr >= ?
            """
            params.append(min_fcf)

        if sector is not None:
            query += """
                AND LOWER(cs.sector) = LOWER(?)
            """
            params.append(sector.strip())

        if min_rev_cagr_5yr is not None:
            query += """
                AND lr.revenue_cagr_5yr >= ?
            """
            params.append(min_rev_cagr_5yr)

        if min_pat_cagr_5yr is not None:
            query += """
                AND lr.pat_cagr_5yr >= ?
            """
            params.append(min_pat_cagr_5yr)

        if max_pe is not None:
            query += """
                AND lv.pe_ratio <= ?
            """
            params.append(max_pe)

        # Highest quality companies first.
        query += """
            ORDER BY
                lr.composite_quality_score DESC,
                c.company_name ASC
        """

        rows = conn.execute(query, params).fetchall()

        results = []

        for row in rows:
            results.append(
                {
                    "company_id": row["company_id"],
                    "company_name": row["company_name"],
                    "ticker": row["ticker"],
                    "sector": row["sector"],
                    "year": row["year"],

                    # Screener metrics
                    "roe_pct": row["return_on_equity_pct"],
                    "operating_profit_margin_pct": row[
                        "operating_profit_margin_pct"
                    ],
                    "net_profit_margin_pct": row[
                        "net_profit_margin_pct"
                    ],
                    "free_cash_flow_cr": row["free_cash_flow_cr"],
                    "revenue_cagr_5yr": row["revenue_cagr_5yr"],
                    "pat_cagr_5yr": row["pat_cagr_5yr"],
                    "eps_cagr_5yr": row["eps_cagr_5yr"],
                    "debt_to_equity": row["debt_to_equity"],
                    "interest_coverage": row["interest_coverage"],
                    "asset_turnover": row["asset_turnover"],
                    "composite_quality_score": row[
                        "composite_quality_score"
                    ],

                    # Valuation metrics
                    "market_cap": row["market_cap"],
                    "pe_ratio": row["pe_ratio"],
                    "pb_ratio": row["pb_ratio"],
                    "dividend_yield": row["dividend_yield"],
                }
            )

        return {
            "count": len(results),
            "filters": {
                "min_roe": min_roe,
                "max_de": max_de,
                "min_fcf": min_fcf,
                "sector": sector,
                "min_rev_cagr_5yr": min_rev_cagr_5yr,
                "min_pat_cagr_5yr": min_pat_cagr_5yr,
                "max_pe": max_pe,
            },
            "results": results,
        }

    finally:
        conn.close()