import pandas as pd

from src.etl.validator import (
    check_pk_uniqueness,
    check_pk_not_null,
    check_fk_validity,
    check_company_year_uniqueness,
    check_required_fields,
    check_positive_sales,
    check_opm,
    check_balance_sheet,
    check_net_cash,
    check_tax_rate,
    check_dividend_cap,
    check_eps_sign,
    check_url,
    check_year,
)


def test_dq01_primary_key_uniqueness():
    df = pd.DataFrame([
        {"company_id": "A", "year": 2024},
        {"company_id": "A", "year": 2023},
    ])

    failures = check_pk_uniqueness(df.to_dict("records"), "company_id")

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-01"
    assert failures[0]["severity"] == "CRITICAL"


def test_dq02_primary_key_not_null():
    df = pd.DataFrame([
        {"company_id": None, "year": 2024},
    ])

    failures = check_pk_not_null(df.to_dict("records"), "company_id")

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-02"
    assert failures[0]["severity"] == "CRITICAL"


def test_dq03_foreign_key_validity():
    df = pd.DataFrame([
        {"company_id": "INVALID", "year": 2024},
    ])

    failures = check_fk_validity(
        df.to_dict("records"),
        "company_id",
        {"VALID"}
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-03"
    assert failures[0]["severity"] == "CRITICAL"


def test_dq04_company_year_uniqueness():
    df = pd.DataFrame([
        {"company_id": "A", "year": 2024},
        {"company_id": "A", "year": 2024},
    ])

    failures = check_company_year_uniqueness(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-04"
    assert failures[0]["severity"] == "CRITICAL"


def test_dq05_required_fields():
    df = pd.DataFrame([
        {"company_id": "A", "year": None},
    ])

    failures = check_required_fields(
        df.to_dict("records"),
        ["company_id", "year"]
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-05"
    assert failures[0]["severity"] == "CRITICAL"


def test_dq06_sales_must_be_positive():
    df = pd.DataFrame([
        {"company_id": "A", "year": 2024, "sales": -100},
    ])

    failures = check_positive_sales(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-06"
    assert failures[0]["severity"] == "WARNING"


def test_dq07_opm_cross_check():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 2024,
            "sales": 100,
            "operating_profit": 20,
            "opm": 50,
        },
    ])

    failures = check_opm(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-07"
    assert failures[0]["severity"] == "WARNING"


def test_dq08_balance_sheet():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 2024,
            "total_assets": 1000,
            "total_liabilities": 400,
            "total_equity": 400,
        },
    ])

    failures = check_balance_sheet(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-08"
    assert failures[0]["severity"] == "WARNING"


def test_dq09_net_cash_cross_check():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 2024,
            "cash": 500,
            "debt": 200,
            "net_cash": 500,
        },
    ])

    failures = check_net_cash(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-09"
    assert failures[0]["severity"] == "WARNING"


def test_dq10_tax_rate():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 2024,
            "tax": 20,
            "profit_before_tax": 100,
            "tax_rate": 50,
        },
    ])

    failures = check_tax_rate(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-10"
    assert failures[0]["severity"] == "WARNING"


def test_dq11_dividend_cap():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 2024,
            "dividend": 150,
            "net_profit": 100,
        },
    ])

    failures = check_dividend_cap(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-11"
    assert failures[0]["severity"] == "WARNING"


def test_dq12_eps_sign():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 2024,
            "eps": -5,
            "net_profit": 100,
        },
    ])

    failures = check_eps_sign(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-12"
    assert failures[0]["severity"] == "WARNING"


def test_dq13_url_validation():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 2024,
            "url": "invalid-url",
        },
    ])

    failures = check_url(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-13"
    assert failures[0]["severity"] == "WARNING"


def test_dq14_year_validation():
    df = pd.DataFrame([
        {
            "company_id": "A",
            "year": 1999,
        },
    ])

    failures = check_year(
        df.to_dict("records")
    )

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-14"
    assert failures[0]["severity"] == "CRITICAL"
