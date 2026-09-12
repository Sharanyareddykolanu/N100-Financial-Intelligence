import sqlite3

conn = sqlite3.connect("nifty100.db")

print("=" * 70)
print("DAY 17 METRIC AVAILABILITY CHECK")
print("=" * 70)

# FCF availability
row = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(free_cash_flow) AS fcf_rows,
        COUNT(CASE WHEN free_cash_flow > 0 THEN 1 END) AS positive_fcf_rows,
        COUNT(CASE WHEN free_cash_flow <= 0 THEN 1 END) AS non_positive_fcf_rows
    FROM company_cashflow
""").fetchone()

print("\nFCF:")
print(f"  Total rows: {row[0]}")
print(f"  FCF available: {row[1]}")
print(f"  Positive FCF: {row[2]}")
print(f"  Zero/negative FCF: {row[3]}")

# CFO and PAT availability
row = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(cf.operating_cash_flow) AS cfo_rows,
        COUNT(pl.net_profit) AS pat_rows
    FROM company_cashflow cf
    LEFT JOIN company_profit_loss pl
        ON cf.company_id = pl.company_id
        AND cf.year = pl.year
""").fetchone()

print("\nCFO / PAT:")
print(f"  Total joined rows: {row[0]}")
print(f"  CFO available: {row[1]}")
print(f"  PAT available: {row[2]}")

# Balance sheet availability
row = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(total_equity) AS equity_rows,
        COUNT(debt) AS debt_rows,
        COUNT(cash) AS cash_rows
    FROM company_balance_sheet
""").fetchone()

print("\nBalance Sheet:")
print(f"  Total rows: {row[0]}")
print(f"  Equity available: {row[1]}")
print(f"  Debt available: {row[2]}")
print(f"  Cash available: {row[3]}")

# Operating profit availability
row = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(operating_profit) AS operating_profit_rows
    FROM company_profit_loss
""").fetchone()

print("\nOperating Profit:")
print(f"  Total rows: {row[0]}")
print(f"  Operating profit available: {row[1]}")

# Interest coverage
print("\nInterest Coverage:")
print("  Cannot calculate because interest expense data is unavailable.")

conn.close()