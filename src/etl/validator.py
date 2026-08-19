import csv
from collections import Counter
from pathlib import Path


# ============================================================
# DQ-01 to DQ-16 — NIFTY 100 DATA QUALITY VALIDATOR
# ============================================================

def failure(rule_id, company_id="", year="", severity="CRITICAL", message=""):
    return {
        "rule_id": rule_id,
        "company_id": company_id,
        "year": year,
        "severity": severity,
        "message": message,
    }


# DQ-01: Primary Key uniqueness
def check_pk_uniqueness(rows, pk_column):
    failures = []
    counts = Counter(row.get(pk_column) for row in rows)

    for key, count in counts.items():
        if key is not None and count > 1:
            failures.append(
                failure(
                    "DQ-01",
                    key,
                    "",
                    "CRITICAL",
                    f"Duplicate primary key: {key}",
                )
            )

    return failures


# DQ-02: Primary Key NOT NULL
def check_pk_not_null(rows, pk_column):
    failures = []

    for row in rows:
        value = row.get(pk_column)

        if value is None or str(value).strip() == "":
            failures.append(
                failure(
                    "DQ-02",
                    value or "",
                    row.get("year", ""),
                    "CRITICAL",
                    f"{pk_column} is NULL or empty",
                )
            )

    return failures


# DQ-03: Foreign Key validity
def check_fk_validity(rows, fk_column, valid_keys):
    failures = []

    for row in rows:
        value = row.get(fk_column)

        if value is not None and str(value).strip() != "":
            if value not in valid_keys:
                failures.append(
                    failure(
                        "DQ-03",
                        value,
                        row.get("year", ""),
                        "CRITICAL",
                        f"Invalid foreign key: {value}",
                    )
                )

    return failures


# DQ-04: Company + Year uniqueness
def check_company_year_uniqueness(rows):
    failures = []
    keys = [
        (row.get("company_id"), row.get("year"))
        for row in rows
    ]

    counts = Counter(keys)

    for (company_id, year), count in counts.items():
        if company_id and year and count > 1:
            failures.append(
                failure(
                    "DQ-04",
                    company_id,
                    year,
                    "CRITICAL",
                    "Duplicate company-year record",
                )
            )

    return failures


# DQ-05: Required fields NOT NULL
def check_required_fields(rows, required_columns):
    failures = []

    for row in rows:
        for column in required_columns:
            value = row.get(column)

            if value is None or str(value).strip() == "":
                failures.append(
                    failure(
                        "DQ-05",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "CRITICAL",
                        f"Required field '{column}' is NULL or empty",
                    )
                )

    return failures


# DQ-06: Sales must be positive
def check_positive_sales(rows, sales_column="sales"):
    failures = []

    for row in rows:
        value = row.get(sales_column)

        try:
            if value is not None and float(value) <= 0:
                failures.append(
                    failure(
                        "DQ-06",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "Sales must be positive",
                    )
                )
        except (TypeError, ValueError):
            failures.append(
                failure(
                    "DQ-06",
                    row.get("company_id", ""),
                    row.get("year", ""),
                    "WARNING",
                    "Sales is not numeric",
                )
            )

    return failures


# DQ-07: Operating Profit Margin cross-check
def check_opm(rows, sales_column="sales",
              operating_profit_column="operating_profit",
              opm_column="opm"):
    failures = []

    for row in rows:
        sales = row.get(sales_column)
        profit = row.get(operating_profit_column)
        opm = row.get(opm_column)

        try:
            if sales is None or profit is None or opm is None:
                continue

            sales = float(sales)
            profit = float(profit)
            opm = float(opm)

            if sales == 0:
                continue

            expected = (profit / sales) * 100

            if abs(expected - opm) > 1.0:
                failures.append(
                    failure(
                        "DQ-07",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "OPM does not match operating profit / sales",
                    )
                )

        except (TypeError, ValueError):
            continue

    return failures


# DQ-08: Balance sheet check
def check_balance_sheet(
    rows,
    assets_column="total_assets",
    liabilities_column="total_liabilities",
    equity_column="total_equity",
):
    failures = []

    for row in rows:
        try:
            assets = float(row.get(assets_column))
            liabilities = float(row.get(liabilities_column))
            equity = float(row.get(equity_column))

            if abs(assets - (liabilities + equity)) > 1.0:
                failures.append(
                    failure(
                        "DQ-08",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "Balance sheet does not balance",
                    )
                )

        except (TypeError, ValueError):
            continue

    return failures


# DQ-09: Net cash cross-check
def check_net_cash(
    rows,
    cash_column="cash",
    debt_column="debt",
    net_cash_column="net_cash",
):
    failures = []

    for row in rows:
        try:
            cash = float(row.get(cash_column))
            debt = float(row.get(debt_column))
            net_cash = float(row.get(net_cash_column))

            expected = cash - debt

            if abs(expected - net_cash) > 1.0:
                failures.append(
                    failure(
                        "DQ-09",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "Net cash does not match cash minus debt",
                    )
                )

        except (TypeError, ValueError):
            continue

    return failures


# DQ-10: Tax rate sanity check
def check_tax_rate(
    rows,
    tax_column="tax",
    profit_before_tax_column="profit_before_tax",
    tax_rate_column="tax_rate",
):
    failures = []

    for row in rows:
        try:
            tax = float(row.get(tax_column))
            pbt = float(row.get(profit_before_tax_column))
            tax_rate = float(row.get(tax_rate_column))

            if pbt == 0:
                continue

            expected = (tax / pbt) * 100

            if abs(expected - tax_rate) > 2.0:
                failures.append(
                    failure(
                        "DQ-10",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "Tax rate cross-check failed",
                    )
                )

        except (TypeError, ValueError):
            continue

    return failures


# DQ-11: Dividend should not exceed profit
def check_dividend_cap(
    rows,
    dividend_column="dividend",
    net_profit_column="net_profit",
):
    failures = []

    for row in rows:
        try:
            dividend = float(row.get(dividend_column))
            profit = float(row.get(net_profit_column))

            if dividend > profit and profit >= 0:
                failures.append(
                    failure(
                        "DQ-11",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "Dividend exceeds net profit",
                    )
                )

        except (TypeError, ValueError):
            continue

    return failures


# DQ-12: EPS sign consistency
def check_eps_sign(
    rows,
    eps_column="eps",
    net_profit_column="net_profit",
):
    failures = []

    for row in rows:
        try:
            eps = float(row.get(eps_column))
            profit = float(row.get(net_profit_column))

            if profit > 0 and eps < 0:
                failures.append(
                    failure(
                        "DQ-12",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "EPS sign inconsistent with net profit",
                    )
                )

            if profit < 0 and eps > 0:
                failures.append(
                    failure(
                        "DQ-12",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        "EPS sign inconsistent with net profit",
                    )
                )

        except (TypeError, ValueError):
            continue

    return failures


# DQ-13: URL validity
def check_url(rows, url_column="url"):
    failures = []

    for row in rows:
        url = row.get(url_column)

        if url is None or str(url).strip() == "":
            failures.append(
                failure(
                    "DQ-13",
                    row.get("company_id", ""),
                    row.get("year", ""),
                    "WARNING",
                    "URL is missing",
                )
            )
        elif not str(url).startswith(("http://", "https://")):
            failures.append(
                failure(
                    "DQ-13",
                    row.get("company_id", ""),
                    row.get("year", ""),
                    "WARNING",
                    "Invalid URL format",
                )
            )

    return failures


# DQ-14: Year validity
def check_year(rows, year_column="year"):
    failures = []

    for row in rows:
        year = row.get(year_column)

        try:
            year_int = int(year)

            if year_int < 2000 or year_int > 2100:
                failures.append(
                    failure(
                        "DQ-14",
                        row.get("company_id", ""),
                        year,
                        "CRITICAL",
                        "Invalid year",
                    )
                )

        except (TypeError, ValueError):
            failures.append(
                failure(
                    "DQ-14",
                    row.get("company_id", ""),
                    year or "",
                    "CRITICAL",
                    "Year is not numeric",
                )
            )

    return failures


# DQ-15: Numeric fields validation
def check_numeric_fields(rows, numeric_columns):
    failures = []

    for row in rows:
        for column in numeric_columns:
            value = row.get(column)

            if value is None or str(value).strip() == "":
                continue

            try:
                float(value)
            except (TypeError, ValueError):
                failures.append(
                    failure(
                        "DQ-15",
                        row.get("company_id", ""),
                        row.get("year", ""),
                        "WARNING",
                        f"{column} must be numeric",
                    )
                )

    return failures


# DQ-16: Company coverage
def check_company_coverage(rows, expected_company_ids):
    actual = {
        row.get("company_id")
        for row in rows
        if row.get("company_id")
    }

    failures = []

    missing = set(expected_company_ids) - actual

    for company_id in sorted(missing):
        failures.append(
            failure(
                "DQ-16",
                company_id,
                "",
                "CRITICAL",
                "Expected company is missing from dataset",
            )
        )

    return failures


# ============================================================
# RUN ALL 16 RULES
# ============================================================

def run_all_validations(rows, valid_fk_keys=None, expected_company_ids=None):
    valid_fk_keys = valid_fk_keys or set()
    expected_company_ids = expected_company_ids or set()

    failures = []

    failures.extend(
        check_pk_uniqueness(rows, "company_id")
    )

    failures.extend(
        check_pk_not_null(rows, "company_id")
    )

    failures.extend(
        check_fk_validity(rows, "company_id", valid_fk_keys)
    )

    failures.extend(
        check_company_year_uniqueness(rows)
    )

    failures.extend(
        check_required_fields(
            rows,
            ["company_id", "year"],
        )
    )

    failures.extend(
        check_positive_sales(rows)
    )

    failures.extend(
        check_opm(rows)
    )

    failures.extend(
        check_balance_sheet(rows)
    )

    failures.extend(
        check_net_cash(rows)
    )

    failures.extend(
        check_tax_rate(rows)
    )

    failures.extend(
        check_dividend_cap(rows)
    )

    failures.extend(
        check_eps_sign(rows)
    )

    failures.extend(
        check_url(rows)
    )

    failures.extend(
        check_year(rows)
    )

    failures.extend(
        check_numeric_fields(
            rows,
            [
                "sales",
                "operating_profit",
                "net_profit",
                "eps",
            ],
        )
    )

    failures.extend(
        check_company_coverage(
            rows,
            expected_company_ids,
        )
    )

    return failures


# ============================================================
# CSV OUTPUT
# ============================================================

def write_validation_failures(failures, output_file="validation_failures.csv"):
    output_path = Path(output_file)

    fieldnames = [
        "rule_id",
        "company_id",
        "year",
        "severity",
        "message",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(failures)

    return output_path
def run_all_validations(rows, valid_fk_keys=None, expected_company_ids=None):
    valid_fk_keys = valid_fk_keys or set()
    expected_company_ids = expected_company_ids or set()

    failures = []

    failures += check_pk_uniqueness(rows, "company_id")
    failures += check_pk_not_null(rows, "company_id")
    failures += check_fk_validity(rows, "company_id", valid_fk_keys)
    failures += check_company_year_uniqueness(rows)

    failures += check_required_fields(rows, ["company_id", "year"])
    failures += check_positive_sales(rows)
    failures += check_opm(rows)
    failures += check_balance_sheet(rows)
    failures += check_net_cash(rows)
    failures += check_tax_rate(rows)
    failures += check_dividend_cap(rows)
    failures += check_eps_sign(rows)
    failures += check_url(rows)
    failures += check_year(rows)
    failures += check_numeric_fields(
        rows,
        ["sales", "operating_profit", "net_profit", "eps"]
    )
    failures += check_company_coverage(
        rows,
        expected_company_ids
    )

    return failures
import csv


def write_validation_failures(
    failures,
    output_file="validation_failures.csv"
):
    fieldnames = [
        "rule_id",
        "company_id",
        "year",
        "severity",
        "message",
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(failures)