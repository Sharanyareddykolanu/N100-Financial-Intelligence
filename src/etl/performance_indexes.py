import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"


INDEXES = [
    ("idx_company_profit_loss_company_year",
     "company_profit_loss", "company_id, year"),

    ("idx_company_balance_sheet_company_year",
     "company_balance_sheet", "company_id, year"),

    ("idx_company_cashflow_company_year",
     "company_cashflow", "company_id, year"),

    ("idx_company_financials_company_year",
     "company_financials", "company_id, year"),

    ("idx_company_price_history_company_year",
     "company_price_history", "company_id, year"),

    ("idx_financial_ratios_company_year",
     "financial_ratios", "company_id, year"),

    ("idx_company_valuation_company_year",
     "company_valuation", "company_id, year"),

    ("idx_peer_percentiles_company_year",
     "peer_percentiles", "company_id, year"),
]


def main():
    with sqlite3.connect(DB_PATH) as conn:
        for index_name, table_name, columns in INDEXES:
            sql = (
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON {table_name} ({columns})"
            )
            conn.execute(sql)

        conn.commit()

    print("SQLite performance indexes created successfully.")

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
              AND name LIKE 'idx_%'
            ORDER BY name
            """
        ).fetchall()

    print(f"Indexes found: {len(rows)}")

    for row in rows:
        print(row[0])


if __name__ == "__main__":
    main()