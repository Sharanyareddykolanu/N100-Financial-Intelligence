import sqlite3

conn = sqlite3.connect("nifty100.db")

query = """
SELECT
    v.company_id,
    v.year,
    v.dividend_yield,
    f.eps
FROM company_valuation v
LEFT JOIN company_financials f
    ON v.company_id = f.company_id
    AND v.year = f.year
WHERE v.dividend_yield IS NOT NULL
LIMIT 10
"""

rows = conn.execute(query).fetchall()

for row in rows:
    print(row)

conn.close()