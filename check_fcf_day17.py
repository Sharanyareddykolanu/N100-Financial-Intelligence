import sqlite3

conn = sqlite3.connect("nifty100.db")

print("=" * 70)
print("DAY 17 FCF SOURCE CHECK")
print("=" * 70)

row = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(free_cash_flow_cr) AS fcf_rows,
        COUNT(CASE WHEN free_cash_flow_cr > 0 THEN 1 END) AS positive_fcf,
        COUNT(CASE WHEN free_cash_flow_cr <= 0 THEN 1 END) AS non_positive_fcf
    FROM financial_ratios
""").fetchone()

print("\nFinancial Ratios FCF:")
print(f"  Total rows: {row[0]}")
print(f"  FCF available: {row[1]}")
print(f"  Positive FCF: {row[2]}")
print(f"  Zero/negative FCF: {row[3]}")

print("\nSample FCF values:")

rows = conn.execute("""
    SELECT company_id, year, free_cash_flow_cr
    FROM financial_ratios
    WHERE free_cash_flow_cr IS NOT NULL
    ORDER BY company_id, year
    LIMIT 10
""").fetchall()

for row in rows:
    print(f"  {row}")

print("\nCFO / PAT ratio availability:")

row = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(
            CASE
                WHEN fr.cash_from_operations_cr IS NOT NULL
                 AND pl.net_profit IS NOT NULL
                 AND pl.net_profit != 0
                THEN 1
            END
        ) AS ratio_rows
    FROM financial_ratios fr
    LEFT JOIN company_profit_loss pl
        ON fr.company_id = pl.company_id
        AND fr.year = pl.year
""").fetchone()

print(f"  Total rows: {row[0]}")
print(f"  CFO/PAT calculable: {row[1]}")

conn.close()