import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/companies", tags=["Companies"])

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_year(value: Optional[str]):
    """Convert YYYY-MM or YYYY into integer year."""
    if value is None:
        return None

    try:
        return int(str(value)[:4])
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Year must be in YYYY-MM format."
        )


def get_company(conn, ticker):
    return conn.execute(
        """
        SELECT
            company_id,
            company_name,
            ticker,
            sector
        FROM companies
        WHERE UPPER(ticker) = UPPER(?)
        """,
        (ticker,)
    ).fetchone()


def get_market_cap_category(market_cap):
    if market_cap is None:
        return None

    if market_cap >= 500000:
        return "Large Cap"
    elif market_cap >= 100000:
        return "Mid Cap"
    return "Small Cap"


def row_to_dict(row):
    return dict(row) if row else None


# ============================================================
# GET ALL COMPANIES
# ============================================================

@router.get("")
def get_companies(
    sector: Optional[str] = Query(None),
    market_cap_category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    conn = get_connection()

    query = """
        SELECT
            c.company_id,
            c.company_name,
            c.ticker,
            COALESCE(s.sector, c.sector) AS broad_sector,
            NULL AS sub_sector,
            r.return_on_equity_pct AS roe_pct,
            NULL AS roce_pct,
            v.market_cap
        FROM companies c
        INNER JOIN company_sector s
            ON c.company_id = s.company_id
        LEFT JOIN financial_ratios r
            ON c.company_id = r.company_id
            AND r.year = (
                SELECT MAX(fr.year)
                FROM financial_ratios fr
                WHERE fr.company_id = c.company_id
            )
        LEFT JOIN company_valuation v
            ON c.company_id = v.company_id
            AND v.year = (
                SELECT MAX(cv.year)
                FROM company_valuation cv
                WHERE cv.company_id = c.company_id
            )
        WHERE c.company_id IN (
            SELECT company_id FROM company_sector
        )
    """

    params = []

    if sector:
        query += """
            AND LOWER(COALESCE(s.sector, c.sector))
                = LOWER(?)
        """
        params.append(sector)

    if search:
        query += """
            AND (
                LOWER(c.company_name) LIKE LOWER(?)
                OR LOWER(c.ticker) LIKE LOWER(?)
            )
        """
        search_value = f"%{search}%"
        params.extend([search_value, search_value])

    query += " ORDER BY c.company_name"

    rows = conn.execute(query, params).fetchall()

    result = []

    for row in rows:
        item = dict(row)

        category = get_market_cap_category(item["market_cap"])

        if market_cap_category:
            if category.lower() != market_cap_category.lower():
                continue

        item.pop("market_cap", None)

        result.append(item)

    conn.close()

    return {
        "count": len(result),
        "companies": result
    }


# ============================================================
# FULL COMPANY PROFILE
# ============================================================

@router.get("/{ticker}")
def get_company_profile(ticker: str):

    conn = get_connection()

    company = get_company(conn, ticker)

    if not company:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found."
        )

    latest_ratio = conn.execute(
        """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 1
        """,
        (company["company_id"],)
    ).fetchone()

    latest_valuation = conn.execute(
        """
        SELECT *
        FROM company_valuation
        WHERE company_id = ?
        ORDER BY year DESC
        LIMIT 1
        """,
        (company["company_id"],)
    ).fetchone()

    sector = conn.execute(
        """
        SELECT sector
        FROM company_sector
        WHERE company_id = ?
        """,
        (company["company_id"],)
    ).fetchone()

    conn.close()

    result = {
        "company_id": company["company_id"],
        "company_name": company["company_name"],
        "ticker": company["ticker"],
        "broad_sector": sector["sector"] if sector else company["sector"],
        "sub_sector": None,
        "roe_pct": (
            latest_ratio["return_on_equity_pct"]
            if latest_ratio else None
        ),
        "roce_pct": None,
        "sector_data": {
            "sector": sector["sector"] if sector else company["sector"]
        },
        "latest_year_kpis": row_to_dict(latest_ratio),
        "latest_valuation": row_to_dict(latest_valuation),
    }

    return result


# ============================================================
# P&L HISTORY
# ============================================================

@router.get("/{ticker}/pl")
def get_profit_loss(
    ticker: str,
    from_year: Optional[str] = Query(None),
    to_year: Optional[str] = Query(None),
):
    conn = get_connection()

    company = get_company(conn, ticker)

    if not company:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found."
        )

    start_year = normalize_year(from_year)
    end_year = normalize_year(to_year)

    query = """
        SELECT
            year,
            sales,
            operating_profit,
            net_profit,
            eps
        FROM company_profit_loss
        WHERE company_id = ?
    """

    params = [company["company_id"]]

    if start_year is not None:
        query += " AND year >= ?"
        params.append(start_year)

    if end_year is not None:
        query += " AND year <= ?"
        params.append(end_year)

    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "ticker": company["ticker"],
        "history": [dict(row) for row in rows]
    }


# ============================================================
# BALANCE SHEET HISTORY
# ============================================================

@router.get("/{ticker}/bs")
def get_balance_sheet(
    ticker: str,
    from_year: Optional[str] = Query(None),
    to_year: Optional[str] = Query(None),
):
    conn = get_connection()

    company = get_company(conn, ticker)

    if not company:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found."
        )

    start_year = normalize_year(from_year)
    end_year = normalize_year(to_year)

    query = """
        SELECT
            year,
            total_assets,
            total_liabilities,
            total_equity,
            cash,
            debt
        FROM company_balance_sheet
        WHERE company_id = ?
    """

    params = [company["company_id"]]

    if start_year is not None:
        query += " AND year >= ?"
        params.append(start_year)

    if end_year is not None:
        query += " AND year <= ?"
        params.append(end_year)

    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "ticker": company["ticker"],
        "history": [dict(row) for row in rows]
    }


# ============================================================
# CASH FLOW HISTORY
# ============================================================

@router.get("/{ticker}/cashflow")
def get_cashflow(
    ticker: str,
    from_year: Optional[str] = Query(None),
    to_year: Optional[str] = Query(None),
):
    conn = get_connection()

    company = get_company(conn, ticker)

    if not company:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found."
        )

    start_year = normalize_year(from_year)
    end_year = normalize_year(to_year)

    query = """
        SELECT
            year,
            operating_cash_flow,
            investing_cash_flow,
            financing_cash_flow,
            free_cash_flow
        FROM company_cashflow
        WHERE company_id = ?
    """

    params = [company["company_id"]]

    if start_year is not None:
        query += " AND year >= ?"
        params.append(start_year)

    if end_year is not None:
        query += " AND year <= ?"
        params.append(end_year)

    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return {
        "ticker": company["ticker"],
        "history": [dict(row) for row in rows]
    }


# ============================================================
# FINANCIAL RATIOS / COMPUTED KPIs
# ============================================================

@router.get("/{ticker}/ratios")
def get_ratios(
    ticker: str,
    year: Optional[int] = Query(None),
):
    conn = get_connection()

    company = get_company(conn, ticker)

    if not company:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found."
        )

    query = """
        SELECT *
        FROM financial_ratios
        WHERE company_id = ?
    """

    params = [company["company_id"]]

    if year is not None:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY year"

    rows = conn.execute(query, params).fetchall()

    conn.close()

    return {
        "ticker": company["ticker"],
        "history": [dict(row) for row in rows]
    }


# ============================================================
# TEARSHEET PDF
# ============================================================

@router.get("/{ticker}/tearsheet")
def get_tearsheet(ticker: str):

    conn = get_connection()

    company = get_company(conn, ticker)

    conn.close()

    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found."
        )

    possible_paths = [
        BASE_DIR / "reports" / "tearsheets" / f"{ticker}_tearsheet.pdf",
        BASE_DIR / "reports" / "tearsheet" / f"{ticker}_tearsheet.pdf",
        BASE_DIR / "output" / "tearsheets" / f"{ticker}_tearsheet.pdf",
        BASE_DIR / "reports" / f"{ticker}_tearsheet.pdf",
    ]

    pdf_path = next(
        (path for path in possible_paths if path.exists()),
        None
    )

    if pdf_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tearsheet PDF not found for {ticker}."
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )