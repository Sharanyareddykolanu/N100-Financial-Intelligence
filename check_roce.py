import sqlite3

conn = sqlite3.connect("nifty100.db")

rows = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(
            CASE
                WHEN pl.operating_profit IS NOT NULL
                 AND bs.total_equity IS NOT NULL
                 AND bs.debt IS NOT NULL
                THEN 1
            END
        ) AS roce_rows
    FROM company_profit_loss pl
    LEFT JOIN company_balance_sheet bs
        ON pl.company_id = bs.company_id
        AND pl.year = bs.year
""").fetchone()

print("=" * 70)
print("ROCE AVAILABILITY CHECK")
print("=" * 70)
print(f"Total rows: {rows[0]}")
print(f"ROCE inputs available: {rows[1]}")

print("\nROCE formula for validation:")
print("ROCE = Operating Profit / (Equity + Debt) * 100")

conn.close()