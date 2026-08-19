import csv
from collections import Counter


def _failure(rule_id, row=None, severity="CRITICAL", message=""):
    row = row or {}
    return {
        "rule_id": rule_id,
        "company_id": row.get("company_id", ""),
        "year": row.get("year", ""),
        "severity": severity,
        "message": message,
    }


# DQ-01: Primary Key uniqueness
def check_pk_uniqueness(rows, pk_column):
    failures = []
    counts = Counter(row.get(pk_column) for row in rows)

    for key, count in counts.items():
        if key is not None and count > 1:
            failures.append({
                "rule_id": "DQ-01",
                "company_id": key,
                "year": "",
                "severity": "CRITICAL",
                "message": f"Duplicate primary key: {key}",
            })

    return failures


# DQ-02: Primary Key NOT NULL
def check_pk_not_null(rows, pk_column):
    failures = []

    for row in rows:
        value = row.get(pk_column)

        if value is None or str(value).strip() == "":
            failures.append({
                "rule_id": "DQ-02",
                "company_id": value or "",
                "year": row.get("year", ""),
                "severity": "CRITICAL",
                "message": f"{pk_column} is NULL or empty",
            })

    return failures


# DQ-03: Foreign Key validity
def check_fk_validity(rows, fk_column, valid_keys):
    failures = []

    for row in rows:
        value = row.get(fk_column)

        if value is not None and str(value).strip() != "":
            if value not in valid_keys:
                failures.append({
                    "rule_id": "DQ-03",
                    "company_id": value,
                    "year": row.get("year", ""),
                    "severity": "CRITICAL",
                    "message": f"Invalid foreign key: {value}",
                })

    return failures


# DQ-04: Company-Year uniqueness
def check_company_year_uniqueness(rows):
    failures = []
    counts = Counter(
        (row.get("company_id"), row.get("year"))
        for row in rows
    )

    for (company_id, year), count in counts.items():
        if company_id and year and count > 1:
            failures.append({
                "rule_id": "DQ-04",
                "company_id": company_id,
                "year": year,
                "severity": "CRITICAL",
                "message": "Duplicate company-year record",
            })

    return failures


# DQ-05: Required fields
def check_required_fields(rows, columns):
    failures = []

    for row in rows:
        for column in columns:
            value = row.get(column)

            if value is None or str(value).strip() == "":
                failures.append(
                    _failure(
                        "DQ-05",
                        row,
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
                    _failure(
                        "DQ-06",
                        row,
                        "WARNING",
                        "Sales must be positive",
                    )
                )
        except (ValueError, TypeError):
            failures.append(
                _failure(
                    "DQ-06",
                    row,
                    "WARNING",
                    "Sales must be numeric",
                )
            )

    return failures


# DQ-07: Operating Profit Margin cross-check
def check_opm(
    rows,
    sales_column="sales",
    operating_profit_column="operating_profit",
    opm_column="opm",
):
    failures = []

    for row in rows:
        try:
            sales = float(row.get(sales_column))
            operating_profit = float(
                row.get(operating_profit_column)
            )
            opm = float(row.get(opm_column))

            if sales == 0:
                continue

            expected_opm = (
                operating_profit / sales
            ) * 100

            if abs(expected_opm - opm) > 1:
                failures.append(
                    _failure(
                        "DQ-07",
                        row,
                        "WARNING",
                        "OPM cross-check failed",
                    )
                )

        except (ValueError, TypeError):
            continue

    return failures


# DQ-08: Balance sheet
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
            liabilities = float(
                row.get(liabilities_column)
            )
            equity = float(row.get(equity_column))

            if abs(assets - (liabilities + equity)) > 1:
                failures.append(
                    _failure(
                        "DQ-08",
                        row,
                        "WARNING",
                        "Balance sheet does not balance",
                    )
                )

        except (ValueError, TypeError):
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

            if abs((cash - debt) - net_cash) > 1:
                failures.append(
                    _failure(
                        "DQ-09",
                        row,
                        "WARNING",
                        "Net cash cross-check failed",
                    )
                )

        except (ValueError, TypeError):
            continue

    return failures


# DQ-10: Tax rate
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

            if abs(expected - tax_rate) > 2:
                failures.append(
                    _failure(
                        "DQ-10",
                        row,
                        "WARNING",
                        "Tax rate cross-check failed",
                    )
                )

        except (ValueError, TypeError):
            continue

    return failures


# DQ-11: Dividend cap
def check_dividend_cap(
    rows,
    dividend_column="dividend",
    profit_column="net_profit",
):
    failures = []

    for row in rows:
        try:
            dividend = float(row.get(dividend_column))
            profit = float(row.get(profit_column))

            if profit >= 0 and dividend > profit:
                failures.append(
                    _failure(
                        "DQ-11",
                        row,
                        "WARNING",
                        "Dividend exceeds net profit",
                    )
                )

        except (ValueError, TypeError):
            continue

    return failures


# DQ-12: EPS sign
def check_eps_sign(
    rows,
    eps_column="eps",
    profit_column="net_profit",
):
    failures = []

    for row in rows:
        try:
            eps = float(row.get(eps_column))
            profit = float(row.get(profit_column))

            if (profit > 0 and eps < 0) or (
                profit < 0 and eps > 0
            ):
                failures.append(
                    _failure(
                        "DQ-12",
                        row,
                        "WARNING",
                        "EPS sign inconsistent with net profit",
                    )
                )

        except (ValueError, TypeError):
            continue

    return failures


# DQ-13: URL validation
def check_url(rows, url_column="url"):
    failures = []

    for row in rows:
        url = row.get(url_column)

        if url is None or str(url).strip() == "":
            failures.append(
                _failure(
                    "DQ-13",
                    row,
                    "WARNING",
                    "URL is missing",
                )
            )
        elif not str(url).startswith(
            ("http://", "https://")
        ):
            failures.append(
                _failure(
                    "DQ-13",
                    row,
                    "WARNING",
                    "Invalid URL",
                )
            )

    return failures


# DQ-14: Year validation
def check_year(rows, year_column="year"):
    failures = []

    for row in rows:
        year = row.get(year_column)

        try:
            year = int(year)

            if year < 2000 or year > 2100:
                failures.append(
                    _failure(
                        "DQ-14",
                        row,
                        "CRITICAL",
                        "Invalid year",
                    )
                )

        except (ValueError, TypeError):
            failures.append(
                _failure(
                    "DQ-14",
                    row,
                    "CRITICAL",
                    "Year is not numeric",
                )
            )

    return failures


# DQ-15: Numeric validation
def check_numeric_fields(
    rows,
    numeric_columns,
):
    failures = []

    for row in rows:
        for column in numeric_columns:
            value = row.get(column)

            if value is None or str(value).strip() == "":
                continue

            try:
                float(value)
            except (ValueError, TypeError):
                failures.append(
                    _failure(
                        "DQ-15",
                        row,
                        "WARNING",
                        f"{column} must be numeric",
                    )
                )

    return failures


# DQ-16: Company coverage
def check_company_coverage(
    rows,
    expected_company_ids,
):
    failures = []

    actual = {
        row.get("company_id")
        for row in rows
        if row.get("company_id")
    }

    for company_id in set(expected_company_ids) - actual:
        failures.append({
            "rule_id": "DQ-16",
            "company_id": company_id,
            "year": "",
            "severity": "CRITICAL",
            "message": "Expected company missing",
        })

    return failures


# ============================================================
# RUN ALL 16 RULES
# ============================================================

def run_all_validations(
    rows,
    valid_fk_keys=None,
    expected_company_ids=None,
):
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
        check_fk_validity(
            rows,
            "company_id",
            valid_fk_keys,
        )
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
# WRITE validation_failures.csv
# ============================================================

def write_validation_failures(
    failures,
    output_file="validation_failures.csv",
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
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(failures)