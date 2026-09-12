import sqlite3

conn = sqlite3.connect("nifty100.db")
cur = conn.cursor()

tables = [
    "company_valuation",
    "company_financials",
    "company_cashflow",
    "company_ratios"
]

for table in tables:
    print(f"\n--- {table} ---")
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        print(row[1])

conn.close()
