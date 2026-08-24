# Day 6 — Data Quality Manual Review

## Database
- 101 companies checked.

## 5 Random Companies Reviewed
- DLF — 2013–2024 — 12 years
- CIPLA — 2013–2024 — 12 years
- AMBUJACEM — 2012–2021 and 2023–2024 — 12 years
- TORNTPHARM — 2013–2024 — 12 years
- JSWENERGY — 2013–2024 — 12 years

## Data Quality Findings
- AMBUJACEM 2022 is missing from the source Excel file.
- JIOFIN has only 2023 and 2024 annual records.
- JIOFIN therefore has fewer than 5 annual years.
- Source verification confirmed these are source-data limitations.
- No loader bug was identified.

## Overall Year Range
- Minimum year: 2011
- Maximum year: 2024
- Unique years: 14

## Validation
- Validator tests: 5/5 passed
- Full test suite: 44/44 passed

## Git
- Changes pushed to origin/main.

## Conclusion
Day 6 Data Quality Manual Review is COMPLETE.
No loader bug was identified.
Source-data gaps for AMBUJACEM and JIOFIN were documented without creating artificial records.
