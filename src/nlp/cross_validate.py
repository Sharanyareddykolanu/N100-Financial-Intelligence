import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_FILE = PROJECT_ROOT / "nifty100.db"
PARSED_FILE = PROJECT_ROOT / "output" / "analysis_parsed.csv"
OUTPUT_FILE = PROJECT_ROOT / "output" / "cagr_cross_validation.csv"


METRIC_MAPPING = {
    "compounded_sales_growth": "revenue_cagr_5yr",
    "compounded_profit_growth": "pat_cagr_5yr",
}


def calculate_divergence(parsed_value, computed_value):
    """Calculate percentage divergence."""

    if pd.isna(computed_value):
        return None

    if computed_value == 0:
        if parsed_value == 0:
            return 0.0
        return float("inf")

    return abs(parsed_value - computed_value) / abs(computed_value) * 100


def cross_validate():

    if not PARSED_FILE.exists():
        raise FileNotFoundError(
            f"Parsed file not found: {PARSED_FILE}"
        )

    parsed_df = pd.read_csv(PARSED_FILE)

    with sqlite3.connect(DB_FILE) as conn:
        ratios_df = pd.read_sql_query(
            """
            SELECT
                company_id,
                revenue_cagr_5yr,
                pat_cagr_5yr
            FROM financial_ratios
            """,
            conn,
        )

    cagr_df = parsed_df[
        parsed_df["metric_type"].isin(METRIC_MAPPING.keys())
    ].copy()

    validation_rows = []

    for _, row in cagr_df.iterrows():

        company_id = row["company_id"]
        metric_type = row["metric_type"]
        period_years = int(row["period_years"])
        parsed_value = float(row["value_pct"])

        ratio_column = METRIC_MAPPING[metric_type]

        # Only 5-year CAGR exists in the Ratio Engine.
        if period_years != 5:

            validation_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "parsed_value_pct": parsed_value,
                    "computed_value_pct": None,
                    "divergence_pct": None,
                    "validation_status": "NOT_COMPARABLE",
                    "review_reason": (
                        "Ratio Engine provides only 5-year CAGR"
                    ),
                }
            )

            continue

        company_ratios = ratios_df[
            ratios_df["company_id"] == company_id
        ]

        if company_ratios.empty:

            validation_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "parsed_value_pct": parsed_value,
                    "computed_value_pct": None,
                    "divergence_pct": None,
                    "validation_status": "REVIEW",
                    "review_reason": (
                        "Company not found in Ratio Engine"
                    ),
                }
            )

            continue

        computed_values = company_ratios[ratio_column].dropna()

        if computed_values.empty:

            validation_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "parsed_value_pct": parsed_value,
                    "computed_value_pct": None,
                    "divergence_pct": None,
                    "validation_status": "REVIEW",
                    "review_reason": "Computed CAGR unavailable",
                }
            )

            continue

        computed_value = float(computed_values.iloc[-1])

        divergence = calculate_divergence(
            parsed_value,
            computed_value,
        )

        if divergence <= 5:
            status = "PASS"
            reason = "Within 5% tolerance"
        else:
            status = "REVIEW"
            reason = "Divergence exceeds 5%"

        validation_rows.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": period_years,
                "parsed_value_pct": parsed_value,
                "computed_value_pct": computed_value,
                "divergence_pct": round(divergence, 2),
                "validation_status": status,
                "review_reason": reason,
            }
        )

    validation_df = pd.DataFrame(validation_rows)

    validation_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("CAGR cross-validation completed.")
    print(f"Rows checked: {len(validation_df)}")
    print()

    print(
        validation_df["validation_status"]
        .value_counts()
        .to_string()
    )

    print()
    print(f"Created: {OUTPUT_FILE}")


if __name__ == "__main__":
    cross_validate()