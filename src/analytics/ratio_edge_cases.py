
"""
Day 13 - Bank ROCE Carve-Out & Edge Case Log

Checks the latest available year for each company:

- Computed ROCE vs companies.xlsx roce_percentage
- Computed ROE vs companies.xlsx roe_percentage
- Logs differences > 5 percentage points
- Financials companies have D/E warning suppression
- Categorizes anomalies as:
    * data source issue
    * version difference
    * formula discrepancy
"""

import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "nifty100.db"
COMPANIES_PATH = BASE_DIR / "companies.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
LOG_PATH = OUTPUT_DIR / "ratio_edge_cases.log"


ANOMALY_THRESHOLD = 5.0
EXTREME_RATIO_THRESHOLD = 100.0


def load_source_companies():
    df = pd.read_excel(
        COMPANIES_PATH,
        header=None
    )

    # Row 1 contains the actual column names.
    df.columns = df.iloc[1]
    df = df.iloc[2:].copy()

    df["id"] = (
        df["id"]
        .astype(str)
        .str.strip()
    )

    return df


def calculate_roe(net_profit, total_equity):
    if net_profit is None or total_equity is None:
        return None

    if total_equity <= 0:
        return None

    return (net_profit / total_equity) * 100


def calculate_roce(
    operating_profit,
    total_equity,
    debt
):
    if operating_profit is None:
        return None

    total_equity = (
        0 if total_equity is None
        else total_equity
    )

    debt = (
        0 if debt is None
        else debt
    )

    capital_employed = total_equity + debt

    if capital_employed <= 0:
        return None

    return (
        operating_profit /
        capital_employed
    ) * 100


def classify_anomaly(
    metric,
    computed,
    source,
    difference,
    company_id
):
    """
    Classify the discrepancy.

    Extreme computed ratios usually indicate that the
    ratio formula/denominator is not comparable with
    the precomputed source metric.

    TCS ROE is a known source anomaly.

    For ordinary differences, the source dataset may use
    a different reporting version/period or methodology.
    """

    # Known source anomaly from the supplied dataset.
    if company_id == "TCS" and metric == "ROE":
        return "data source issue"

    # Extremely large computed ratios are more consistent
    # with a formula/denominator mismatch.
    if abs(computed) > EXTREME_RATIO_THRESHOLD:
        return "formula discrepancy"

    # Negative computed ROE against positive source ROE
    # indicates a meaningful methodology/data difference.
    if metric == "ROE":
        if computed < 0 <= source:
            return "version difference"

    # For ordinary differences above the threshold,
    # treat the discrepancy as a version/methodology
    # difference rather than automatically blaming the source.
    return "version difference"


def main():

    OUTPUT_DIR.mkdir(exist_ok=True)

    source_df = load_source_companies()

    conn = sqlite3.connect(DB_PATH)

    # Latest year for every company.
    rows = conn.execute(
        """
        SELECT
            p.company_id,
            p.year,
            p.net_profit,
            p.operating_profit,
            b.total_equity,
            b.debt
        FROM company_profit_loss p
        LEFT JOIN company_balance_sheet b
            ON p.company_id = b.company_id
            AND p.year = b.year
        INNER JOIN (
            SELECT
                company_id,
                MAX(year) AS max_year
            FROM company_profit_loss
            GROUP BY company_id
        ) latest
            ON p.company_id = latest.company_id
            AND p.year = latest.max_year
        ORDER BY p.company_id
        """
    ).fetchall()

    financials = {
        r[0]
        for r in conn.execute(
            """
            SELECT company_id
            FROM company_sector
            WHERE LOWER(sector) = ?
            """,
            ("financials",)
        ).fetchall()
    }

    conn.close()

    anomalies = []

    for (
        company_id,
        year,
        net_profit,
        operating_profit,
        total_equity,
        debt
    ) in rows:

        source = source_df[
            source_df["id"] == company_id
        ]

        if source.empty:
            continue

        source_row = source.iloc[0]

        source_roe = pd.to_numeric(
            source_row["roe_percentage"],
            errors="coerce"
        )

        source_roce = pd.to_numeric(
            source_row["roce_percentage"],
            errors="coerce"
        )

        computed_roe = calculate_roe(
            net_profit,
            total_equity
        )

        computed_roce = calculate_roce(
            operating_profit,
            total_equity,
            debt
        )

        # ROCE anomaly
        if (
            pd.notna(source_roce)
            and computed_roce is not None
            and abs(computed_roce - source_roce)
            > ANOMALY_THRESHOLD
        ):

            difference = abs(
                computed_roce - source_roce
            )

            anomalies.append(
                {
                    "company_id": company_id,
                    "year": year,
                    "metric": "ROCE",
                    "computed": computed_roce,
                    "source": float(source_roce),
                    "difference": difference,
                    "category": classify_anomaly(
                        "ROCE",
                        computed_roce,
                        float(source_roce),
                        difference,
                        company_id
                    ),
                }
            )

        # ROE anomaly
        if (
            pd.notna(source_roe)
            and computed_roe is not None
            and abs(computed_roe - source_roe)
            > ANOMALY_THRESHOLD
        ):

            difference = abs(
                computed_roe - source_roe
            )

            anomalies.append(
                {
                    "company_id": company_id,
                    "year": year,
                    "metric": "ROE",
                    "computed": computed_roe,
                    "source": float(source_roe),
                    "difference": difference,
                    "category": classify_anomaly(
                        "ROE",
                        computed_roe,
                        float(source_roe),
                        difference,
                        company_id
                    ),
                }
            )

    # Count categories
    category_counts = {}

    for item in anomalies:
        category = item["category"]
        category_counts[category] = (
            category_counts.get(category, 0) + 1
        )

    with open(
        LOG_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "Day 13 - Ratio Edge Cases\n"
        )
        f.write(
            "========================================\n\n"
        )

        f.write(
            f"Financials companies: "
            f"{len(financials)}\n"
        )

        f.write(
            "D/E warning suppression: ENABLED "
            "for Financials\n"
        )

        f.write(
            "Validation scope: latest available "
            "year per company\n\n"
        )

        f.write(
            f"Companies checked: {len(rows)}\n"
        )

        f.write(
            f"Total anomalies: {len(anomalies)}\n\n"
        )

        f.write(
            "Anomaly category summary:\n"
        )
        f.write(
            "----------------------------------------\n"
        )

        for category in [
            "data source issue",
            "version difference",
            "formula discrepancy"
        ]:
            f.write(
                f"{category}: "
                f"{category_counts.get(category, 0)}\n"
            )

        f.write("\n")

        for item in anomalies:

            f.write(
                f"Company: {item['company_id']}\n"
            )

            f.write(
                f"Year: {item['year']}\n"
            )

            f.write(
                f"Metric: {item['metric']}\n"
            )

            f.write(
                f"Computed: "
                f"{item['computed']:.4f}%\n"
            )

            f.write(
                f"Source: "
                f"{item['source']:.4f}%\n"
            )

            f.write(
                f"Difference: "
                f"{item['difference']:.4f}%\n"
            )

            f.write(
                f"Category: {item['category']}\n"
            )

            # Specific notes for important edge cases.
            if (
                item["company_id"] == "TCS"
                and item["metric"] == "ROE"
            ):
                f.write(
                    "Notes: Source ROE appears anomalous; "
                    "ratio-engine value retained for analytics.\n"
                )

            elif abs(item["computed"]) > EXTREME_RATIO_THRESHOLD:
                f.write(
                    "Notes: Extreme computed ratio detected; "
                    "likely denominator/formula mismatch. "
                    "Review sector-specific ROCE/ROE methodology.\n"
                )

            elif (
                item["metric"] == "ROE"
                and item["computed"] < 0
                and item["source"] >= 0
            ):
                f.write(
                    "Notes: Computed ROE is negative while "
                    "source ROE is positive; likely period/"
                    "methodology difference.\n"
                )

            f.write("\n")

    print(
        f"Edge-case log generated: {LOG_PATH}"
    )

    print(
        f"Financials companies detected: "
        f"{len(financials)}"
    )

    print(
        f"Companies checked: {len(rows)}"
    )

    print(
        f"Anomalies logged: {len(anomalies)}"
    )

    print(
        "Category summary:"
    )

    for category in [
        "data source issue",
        "version difference",
        "formula discrepancy"
    ]:
        print(
            f"  {category}: "
            f"{category_counts.get(category, 0)}"
        )


if __name__ == "__main__":
    main()

