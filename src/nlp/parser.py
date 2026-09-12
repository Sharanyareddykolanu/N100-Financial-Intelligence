import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

ANALYSIS_FILE = DATA_DIR / "1788501604303-57986a9b-analysis.xlsx"

PARSED_FILE = OUTPUT_DIR / "analysis_parsed.csv"
FAILURES_FILE = OUTPUT_DIR / "parse_failures.csv"


# Examples:
# 10 Years: 21%
# 5 Years: 24%
# 3 Years: 17%
# TTM: 43%
# 1 Year: -2%
PATTERN = re.compile(
    r"(?:(\d+)\s*Years?|(\d+)\s*Year|TTM|Last\s+Year)"
    r"\s*:?\s*(-?[\d.]+)\s*%"
)


TARGET_METRICS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]


def parse_metric_text(raw_text):
    """Extract period and percentage value from analysis text."""

    if pd.isna(raw_text):
        return None, None

    text = str(raw_text).strip()

    match = PATTERN.search(text)

    if not match:
        return None, None

    years = match.group(1) or match.group(2)

    # TTM / Last Year are not multi-year CAGR periods.
    if years is None:
        period_years = 1
    else:
        period_years = int(years)

    value_pct = float(match.group(3))

    return period_years, value_pct


def parse_analysis():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not ANALYSIS_FILE.exists():
        raise FileNotFoundError(
            f"Analysis file not found: {ANALYSIS_FILE}"
        )

    # Row 1 contains the real column headers.
    df = pd.read_excel(
        ANALYSIS_FILE,
        header=1,
    )

    print("Columns detected:")
    print(list(df.columns))

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():

        company_id = str(row["company_id"]).strip()

        if not company_id or company_id == "nan":
            continue

        for metric_type in TARGET_METRICS:

            raw_text = row[metric_type]

            period_years, value_pct = parse_metric_text(raw_text)

            if period_years is None:
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "raw_text": str(raw_text),
                        "reason": "Regex pattern did not match",
                    }
                )
                continue

            parsed_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ],
    )

    failures_df = pd.DataFrame(
        failure_rows,
        columns=[
            "company_id",
            "metric_type",
            "raw_text",
            "reason",
        ],
    )

    parsed_df.to_csv(
        PARSED_FILE,
        index=False,
    )

    failures_df.to_csv(
        FAILURES_FILE,
        index=False,
    )

    print()
    print("Parser completed successfully.")
    print(f"Parsed rows: {len(parsed_df)}")
    print(f"Parse failures: {len(failures_df)}")
    print()
    print(f"Created: {PARSED_FILE}")
    print(f"Created: {FAILURES_FILE}")


if __name__ == "__main__":
    parse_analysis()