from pathlib import Path
import sqlite3
import re
import pandas as pd

from src.etl.normaliser import normalize_year, normalize_ticker


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SUPPORTING_DIR = BASE_DIR / "supporting datasets"
DB_PATH = BASE_DIR / "nifty100.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
OUTPUT_DIR = BASE_DIR / "output"


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path=DB_PATH, schema_path=SCHEMA_PATH):
    conn = get_connection(db_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    conn.executescript(schema)
    conn.commit()

    return conn


def _read_excel(path):
    return pd.read_excel(path, header=1)


def _clean_company_id(value):
    if pd.isna(value):
        return None
    return normalize_ticker(value)


def _clean_number(value):
    if pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _column(df, *names):
    """
    Find a column using flexible matching.
    """
    normalized = {
        re.sub(r"[^a-z0-9]", "", str(c).lower()): c
        for c in df.columns
    }

    for name in names:
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if key in normalized:
            return normalized[key]

    return None


def _value(row, df, *names):
    col = _column(df, *names)

    if col is None:
        return None

    return row.get(col)


def _load_companies(conn):
    path = DATA_DIR / "companies.xlsx"
    df = _read_excel(path)

    companies = {}

    # Official companies
    for _, row in df.iterrows():
        company_id = _clean_company_id(
            _value(row, df, "id", "company_id", "ticker")
        )

        if not company_id:
            continue

        name = _value(
            row,
            df,
            "company_name",
            "company",
            "name"
        )

        if pd.isna(name) or name is None:
            name = company_id

        companies[company_id] = (
            company_id,
            str(name).strip(),
            company_id,
            None
        )

    # Collect IDs from all datasets to avoid FK failures
    files = (
        list(DATA_DIR.glob("*.xlsx"))
        + list(SUPPORTING_DIR.glob("*.xlsx"))
    )

    for path in files:
        try:
            source = _read_excel(path)
        except Exception:
            continue

        col = _column(
            source,
            "company_id",
            "id",
            "ticker",
            "symbol"
        )

        if col is None:
            continue

        for value in source[col].dropna():
            company_id = _clean_company_id(value)

            if company_id and company_id not in companies:
                companies[company_id] = (
                    company_id,
                    company_id,
                    company_id,
                    None
                )

    rows = list(companies.values())

    conn.executemany(
        """
        INSERT OR IGNORE INTO companies
        (company_id, company_name, ticker, sector)
        VALUES (?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_sectors(conn):
    path = SUPPORTING_DIR / "sectors.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():
        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        sector = _value(
            row,
            df,
            "broad_sector",
            "sector",
            "industry"
        )

        if not company_id or pd.isna(sector):
            continue

        rows.append(
            (company_id, str(sector).strip())
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_sector
        (company_id, sector)
        VALUES (?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_profit_loss(conn):
    path = DATA_DIR / "profitandloss.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():

        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        year = normalize_year(
            _value(row, df, "year", "financial_year", "fy")
        )

        if not company_id or year is None:
            continue

        rows.append(
            (
                company_id,
                year,
                _clean_number(_value(row, df, "sales", "revenue")),
                _clean_number(
                    _value(row, df, "operating_profit", "op_profit")
                ),
                _clean_number(
                    _value(row, df, "net_profit", "profit")
                ),
                _clean_number(_value(row, df, "eps"))
            )
        )

    rows = list({
        (r[0], r[1]): r
        for r in rows
    }.values())

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_profit_loss
        (company_id, year, sales, operating_profit, net_profit, eps)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_balance_sheet(conn):
    path = DATA_DIR / "balancesheet.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():

        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        year = normalize_year(
            _value(row, df, "year", "financial_year", "fy")
        )

        if not company_id or year is None:
            continue

        equity = _clean_number(
            _value(row, df, "total_equity", "equity")
        )

        if equity is None:
            capital = _clean_number(
                _value(row, df, "equity_capital")
            ) or 0

            reserves = _clean_number(
                _value(row, df, "reserves")
            ) or 0

            equity = capital + reserves

        rows.append(
            (
                company_id,
                year,
                _clean_number(
                    _value(row, df, "total_assets", "assets")
                ),
                _clean_number(
                    _value(
                        row,
                        df,
                        "total_liabilities",
                        "liabilities"
                    )
                ),
                equity,
                _clean_number(
                    _value(row, df, "cash", "other_asset")
                ),
                _clean_number(
                    _value(row, df, "debt", "borrowings")
                )
            )
        )

    rows = list({
        (r[0], r[1]): r
        for r in rows
    }.values())

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_balance_sheet
        (company_id, year, total_assets, total_liabilities,
         total_equity, cash, debt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_cashflow(conn):
    path = DATA_DIR / "cashflow.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():

        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        year = normalize_year(
            _value(row, df, "year", "financial_year", "fy")
        )

        if not company_id or year is None:
            continue

        rows.append(
            (
                company_id,
                year,
                _clean_number(
                    _value(
                        row,
                        df,
                        "operating_cash_flow",
                        "cash_from_operating"
                    )
                ),
                _clean_number(
                    _value(
                        row,
                        df,
                        "investing_cash_flow",
                        "cash_from_investing"
                    )
                ),
                _clean_number(
                    _value(
                        row,
                        df,
                        "financing_cash_flow",
                        "cash_from_financing"
                    )
                ),
                _clean_number(
                    _value(
                        row,
                        df,
                        "free_cash_flow"
                    )
                )
            )
        )

    rows = list({
        (r[0], r[1]): r
        for r in rows
    }.values())

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_cashflow
        (company_id, year, operating_cash_flow,
         investing_cash_flow, financing_cash_flow,
         free_cash_flow)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_ratios(conn):
    path = SUPPORTING_DIR / "financial_ratios.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():

        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        year = normalize_year(
            _value(row, df, "year", "financial_year", "fy")
        )

        if not company_id or year is None:
            continue

        rows.append(
            (
                company_id,
                year,
                _clean_number(
                    _value(row, df, "opm", "operating_profit_margin")
                ),
                _clean_number(
                    _value(row, df, "tax_rate")
                ),
                _clean_number(
                    _value(row, df, "net_cash")
                )
            )
        )

    rows = list({
        (r[0], r[1]): r
        for r in rows
    }.values())

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_ratios
        (company_id, year, opm, tax_rate, net_cash)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_valuation(conn):
    path = SUPPORTING_DIR / "market_cap.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():

        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        year = normalize_year(
            _value(row, df, "year", "financial_year", "fy")
        )

        if not company_id or year is None:
            continue

        rows.append(
            (
                company_id,
                year,
                _clean_number(
                    _value(row, df, "market_cap")
                ),
                _clean_number(
                    _value(row, df, "pe_ratio", "pe")
                ),
                _clean_number(
                    _value(row, df, "pb_ratio", "pb")
                ),
                _clean_number(
                    _value(row, df, "dividend_yield")
                )
            )
        )

    rows = list({
        (r[0], r[1]): r
        for r in rows
    }.values())

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_valuation
        (company_id, year, market_cap, pe_ratio,
         pb_ratio, dividend_yield)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_prices(conn):
    path = SUPPORTING_DIR / "stock_prices.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():

        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        year = normalize_year(
            _value(row, df, "year", "financial_year", "fy")
        )

        if not company_id or year is None:
            continue

        rows.append(
            (
                company_id,
                year,
                _clean_number(
                    _value(row, df, "close_price", "close")
                ),
                _clean_number(
                    _value(row, df, "high_price", "high")
                ),
                _clean_number(
                    _value(row, df, "low_price", "low")
                )
            )
        )

    rows = list({
        (r[0], r[1]): r
        for r in rows
    }.values())

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_price_history
        (company_id, year, close_price, high_price, low_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def _load_financials(conn):
    """
    Load company_financials where compatible data exists.
    """

    path = DATA_DIR / "profitandloss.xlsx"

    if not path.exists():
        return 0, 0

    df = _read_excel(path)
    rows = []

    for _, row in df.iterrows():

        company_id = _clean_company_id(
            _value(row, df, "company_id", "id", "ticker")
        )

        year = normalize_year(
            _value(row, df, "year", "financial_year", "fy")
        )

        if not company_id or year is None:
            continue

        rows.append(
            (
                company_id,
                year,
                _clean_number(
                    _value(row, df, "revenue", "sales")
                ),
                _clean_number(
                    _value(row, df, "profit", "net_profit")
                ),
                _clean_number(
                    _value(row, df, "eps")
                ),
                _clean_number(
                    _value(row, df, "dividend")
                )
            )
        )

    rows = list({
        (r[0], r[1]): r
        for r in rows
    }.values())

    conn.executemany(
        """
        INSERT OR REPLACE INTO company_financials
        (company_id, year, revenue, profit, eps, dividend)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows
    )

    return len(rows), 0


def load_all(db_path=DB_PATH):

    OUTPUT_DIR.mkdir(exist_ok=True)

    conn = initialize_database(db_path)

    audit = []

    loaders = [
        ("companies.xlsx", "companies", _load_companies),
        ("sectors.xlsx", "company_sector", _load_sectors),
        ("profitandloss.xlsx", "company_profit_loss", _load_profit_loss),
        ("balancesheet.xlsx", "company_balance_sheet", _load_balance_sheet),
        ("cashflow.xlsx", "company_cashflow", _load_cashflow),
        (
            "financial_ratios.xlsx",
            "company_ratios",
            _load_ratios
        ),
        (
            "market_cap.xlsx",
            "company_valuation",
            _load_valuation
        ),
        (
            "stock_prices.xlsx",
            "company_price_history",
            _load_prices
        ),
        (
            "profitandloss.xlsx",
            "company_financials",
            _load_financials
        )
    ]

    for filename, table, loader in loaders:

        try:
            loaded, rejected = loader(conn)

        except Exception as e:
            print(f"ERROR loading {filename}: {e}")
            loaded = 0
            rejected = 0

        audit.append(
            {
                "source_file": filename,
                "table_name": table,
                "rows_loaded": loaded,
                "rows_rejected": rejected
            }
        )

    conn.commit()

    fk_errors = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    audit_df = pd.DataFrame(audit)

    audit_df["fk_errors"] = len(fk_errors)

    audit_df.to_csv(
        OUTPUT_DIR / "load_audit.csv",
        index=False
    )

    conn.close()

    return audit_df, fk_errors