import sqlite3
import pandas as pd

conn = sqlite3.connect("nifty100.db")

ids = ["AGTL", "AMBUJACEM", "GODREJCP", "JINDALSTEL"]

for company_id in ids:
    print(f"\n========== {company_id} ==========")

    df = pd.read_sql_query(
        """
        SELECT company_id, year,
               return_on_equity_pct,
               debt_to_equity,
               interest_coverage,
               operating_profit_margin_pct,
               free_cash_flow_cr,
               revenue_cagr_5yr,
               pat_cagr_5yr,
               eps_cagr_5yr,
               dividend_payout_ratio_pct
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year
        """,
        conn,
        params=[company_id]
    )

    print(df.to_string(index=False))

conn.close()
