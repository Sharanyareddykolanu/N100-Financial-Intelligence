import sqlite3

c = sqlite3.connect("nifty100.db")

for company in ["ADANIGREEN", "ADANIPOWER"]:
    print("\n", company)
    rows = c.execute(
        """
        SELECT year, net_profit, eps
        FROM company_profit_loss
        WHERE company_id = ?
        ORDER BY year
        """,
        (company,),
    ).fetchall()

    for row in rows:
        print(row)

c.close()