from pathlib import Path
import sqlite3

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/sectors", tags=["Sectors"])

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("")
def get_sectors():
    """
    Return all sectors with company count and median
    ROE, P/E and D/E.
    """

    conn = get_connection()

    try:
        sectors = conn.execute(
            """
            SELECT DISTINCT sector
            FROM company_sector
            ORDER BY sector
            """
        ).fetchall()

        results = []

        for sector_row in sectors:
            sector = sector_row["sector"]

            row = conn.execute(
                """
                WITH latest_ratios AS (
                    SELECT
                        fr.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY company_id
                            ORDER BY year DESC
                        ) AS rn
                    FROM financial_ratios fr
                    WHERE company_id IN (
                        SELECT company_id
                        FROM company_sector
                        WHERE sector = ?
                    )
                ),
                latest_valuation AS (
                    SELECT
                        cv.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY company_id
                            ORDER BY year DESC
                        ) AS rn
                    FROM company_valuation cv
                    WHERE company_id IN (
                        SELECT company_id
                        FROM company_sector
                        WHERE sector = ?
                    )
                )
                SELECT
                    COUNT(DISTINCT lr.company_id) AS company_count,
                    (
                        SELECT AVG(x.return_on_equity_pct)
                        FROM (
                            SELECT return_on_equity_pct
                            FROM latest_ratios
                            WHERE rn = 1
                              AND return_on_equity_pct IS NOT NULL
                            ORDER BY return_on_equity_pct
                            LIMIT 2 - (
                                SELECT COUNT(*)
                                FROM latest_ratios
                                WHERE rn = 1
                                  AND return_on_equity_pct IS NOT NULL
                            ) % 2
                            OFFSET (
                                SELECT (COUNT(*) - 1) / 2
                                FROM latest_ratios
                                WHERE rn = 1
                                  AND return_on_equity_pct IS NOT NULL
                            )
                        ) x
                    ) AS median_roe
                """,
                (sector, sector),
            ).fetchone()

            # SQLite median calculation is easier and safer in Python.
            ratios = conn.execute(
                """
                SELECT
                    fr.return_on_equity_pct,
                    fr.debt_to_equity
                FROM financial_ratios fr
                INNER JOIN company_sector cs
                    ON cs.company_id = fr.company_id
                WHERE cs.sector = ?
                  AND fr.year = (
                      SELECT MAX(fr2.year)
                      FROM financial_ratios fr2
                      WHERE fr2.company_id = fr.company_id
                  )
                """,
                (sector,),
            ).fetchall()

            valuations = conn.execute(
                """
                SELECT cv.pe_ratio
                FROM company_valuation cv
                INNER JOIN company_sector cs
                    ON cs.company_id = cv.company_id
                WHERE cs.sector = ?
                  AND cv.year = (
                      SELECT MAX(cv2.year)
                      FROM company_valuation cv2
                      WHERE cv2.company_id = cv.company_id
                  )
                  AND cv.pe_ratio IS NOT NULL
                """,
                (sector,),
            ).fetchall()

            def median(values):
                values = sorted(
                    float(v)
                    for v in values
                    if v is not None
                )

                if not values:
                    return None

                n = len(values)

                if n % 2:
                    return values[n // 2]

                return (values[n // 2 - 1] + values[n // 2]) / 2

            roe_values = [
                r["return_on_equity_pct"]
                for r in ratios
            ]

            de_values = [
                r["debt_to_equity"]
                for r in ratios
            ]

            pe_values = [
                r["pe_ratio"]
                for r in valuations
            ]

            results.append(
                {
                    "sector": sector,
                    "company_count": len(ratios),
                    "median_roe": median(roe_values),
                    "median_pe": median(pe_values),
                    "median_de": median(de_values),
                }
            )

        return {
            "count": len(results),
            "sectors": results,
        }

    finally:
        conn.close()


@router.get("/{sector}/companies")
def get_sector_companies(sector: str):
    """
    Return all companies in a sector with latest-year KPIs.
    """

    conn = get_connection()

    try:
        sector_row = conn.execute(
            """
            SELECT DISTINCT sector
            FROM company_sector
            WHERE LOWER(sector) = LOWER(?)
            """,
            (sector,),
        ).fetchone()

        if sector_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown sector: {sector}",
            )

        actual_sector = sector_row["sector"]

        rows = conn.execute(
            """
            SELECT
                c.company_id,
                c.company_name,
                c.ticker,
                cs.sector,
                fr.year,
                fr.net_profit_margin_pct,
                fr.operating_profit_margin_pct,
                fr.return_on_equity_pct,
                fr.debt_to_equity,
                fr.interest_coverage,
                fr.asset_turnover,
                fr.free_cash_flow_cr,
                fr.revenue_cagr_5yr,
                fr.pat_cagr_5yr,
                fr.eps_cagr_5yr,
                fr.composite_quality_score
            FROM companies c
            INNER JOIN company_sector cs
                ON cs.company_id = c.company_id
            LEFT JOIN financial_ratios fr
                ON fr.company_id = c.company_id
                AND fr.year = (
                    SELECT MAX(fr2.year)
                    FROM financial_ratios fr2
                    WHERE fr2.company_id = c.company_id
                )
            WHERE LOWER(cs.sector) = LOWER(?)
            ORDER BY
                fr.composite_quality_score DESC,
                c.company_name ASC
            """,
            (actual_sector,),
        ).fetchall()

        companies = []

        for row in rows:
            companies.append(
                {
                    "company_id": row["company_id"],
                    "company_name": row["company_name"],
                    "ticker": row["ticker"],
                    "sector": row["sector"],
                    "year": row["year"],
                    "kpis": {
                        "net_profit_margin_pct": row[
                            "net_profit_margin_pct"
                        ],
                        "operating_profit_margin_pct": row[
                            "operating_profit_margin_pct"
                        ],
                        "roe_pct": row[
                            "return_on_equity_pct"
                        ],
                        "debt_to_equity": row[
                            "debt_to_equity"
                        ],
                        "interest_coverage": row[
                            "interest_coverage"
                        ],
                        "asset_turnover": row[
                            "asset_turnover"
                        ],
                        "free_cash_flow_cr": row[
                            "free_cash_flow_cr"
                        ],
                        "revenue_cagr_5yr": row[
                            "revenue_cagr_5yr"
                        ],
                        "pat_cagr_5yr": row[
                            "pat_cagr_5yr"
                        ],
                        "eps_cagr_5yr": row[
                            "eps_cagr_5yr"
                        ],
                        "composite_quality_score": row[
                            "composite_quality_score"
                        ],
                    },
                }
            )

        return {
            "sector": actual_sector,
            "count": len(companies),
            "companies": companies,
        }

    finally:
        conn.close()