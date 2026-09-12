# Day 29 — NLP Analysis Text Parser

## Completed
- Parsed analysis.xlsx text fields using regex.
- Extracted:
  - compounded_sales_growth
  - compounded_profit_growth
  - stock_price_cagr
  - roe
- Generated analysis_parsed.csv.
- Generated parse_failures.csv.
- Parse failures: 0.
- Cross-validated 5-year sales and profit CAGR values against the Ratio Engine.
- Divergence threshold: 5%.
- Generated cagr_cross_validation.csv.

## Validation Results
- Parsed rows: 80
- Parse failures: 0
- CAGR validation rows: 40
- PASS: 8
- REVIEW: 2
- NOT_COMPARABLE: 30

## Manual Review
- SBILIFE compounded_profit_growth: 18.64% divergence.
- WIPRO compounded_profit_growth: 6.20% divergence.

## Note
30 records are marked NOT_COMPARABLE because the Ratio Engine currently provides only 5-year CAGR values.
