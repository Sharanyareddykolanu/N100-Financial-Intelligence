import sqlite3

DB = "nifty100.db"

conn = sqlite3.connect(DB)

print("=" * 60)
print("DAY 14 - FINANCIAL RATIOS FINAL VALIDATION")
print("=" * 60)

# 1. Row count
count = conn.execute(
    "SELECT COUNT(*) FROM financial_ratios"
).fetchone()[0]

print(f"\n1. Row count: {count}")
print("   PASS" if count >= 1100 else "   FAIL")

# 2. Duplicate company/year records
duplicates = conn.execute("""
    SELECT company_id, year, COUNT(*)
    FROM financial_ratios
    GROUP BY company_id, year
    HAVING COUNT(*) > 1
""").fetchall()

print(f"\n2. Duplicate records: {len(duplicates)}")
print("   PASS" if len(duplicates) == 0 else "   FAIL")

# 3. KPI completeness
kpis = [
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "debt_to_equity",
    "interest_coverage",
    "asset_turnover",
    "free_cash_flow_cr",
    "earnings_per_share",
    "dividend_payout_ratio_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "composite_quality_score",
]

print("\n3. KPI completeness:")

for kpi in kpis:
    total = conn.execute(
        f"SELECT COUNT(*) FROM financial_ratios WHERE {kpi} IS NOT NULL"
    ).fetchone()[0]

    print(f"   {kpi}: {total}/{count}")

# 4. Sample calculated records
print("\n4. Sample calculated records:")

samples = conn.execute("""
    SELECT
        company_id,
        year,
        net_profit_margin_pct,
        operating_profit_margin_pct,
        return_on_equity_pct,
        debt_to_equity,
        asset_turnover,
        free_cash_flow_cr,
        earnings_per_share,
        revenue_cagr_5yr,
        pat_cagr_5yr,
        eps_cagr_5yr,
        composite_quality_score
    FROM financial_ratios
    LIMIT 5
""").fetchall()

for row in samples:
    print(row)

# 5. Check invalid negative quality scores
invalid_scores = conn.execute("""
    SELECT COUNT(*)
    FROM financial_ratios
    WHERE composite_quality_score < 0
       OR composite_quality_score > 100
""").fetchone()[0]

print(f"\n5. Invalid quality scores: {invalid_scores}")
print("   PASS" if invalid_scores == 0 else "   FAIL")

# 6. Expected unavailable KPIs
interest_count = conn.execute("""
    SELECT COUNT(*)
    FROM financial_ratios
    WHERE interest_coverage IS NOT NULL
""").fetchone()[0]

dividend_count = conn.execute("""
    SELECT COUNT(*)
    FROM financial_ratios
    WHERE dividend_payout_ratio_pct IS NOT NULL
""").fetchone()[0]

print("\n6. Source-data limitations:")
print(f"   Interest Coverage populated: {interest_count}/{count}")
print(f"   Dividend Payout populated: {dividend_count}/{count}")

if interest_count == 0:
    print("   Interest Coverage: NOT CALCULATED - interest expense unavailable")

if dividend_count == 0:
    print("   Dividend Payout: NOT CALCULATED - DPS unavailable")

print("\n" + "=" * 60)
print("DAY 14 VALIDATION COMPLETE")
print("=" * 60)

conn.close()