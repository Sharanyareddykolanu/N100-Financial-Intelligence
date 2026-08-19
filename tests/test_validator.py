from src.etl.validator import check_pk_uniqueness, check_pk_not_null
from src.etl.validator import (
    check_pk_uniqueness,
    check_pk_not_null,
    check_fk_validity,
)


def test_dq01_detects_duplicate():
    rows = [
        {"company_id": "TCS"},
        {"company_id": "INFY"},
        {"company_id": "TCS"},
    ]

    failures = check_pk_uniqueness(rows, "company_id")

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-01"
    assert failures[0]["company_id"] == "TCS"
    assert failures[0]["severity"] == "CRITICAL"

def test_dq01_no_duplicate():
    rows = [
        {"company_id": "TCS"},
        {"company_id": "INFY"},
        {"company_id": "RELIANCE"},
    ]

    failures = check_pk_uniqueness(rows, "company_id")

    assert failures == []


def test_dq02_no_null_pk():
    rows = [
        {"company_id": "TCS"},
        {"company_id": "INFY"},
        {"company_id": "RELIANCE"},
    ]

    failures = check_pk_not_null(rows, "company_id")

    assert failures == []


def test_dq03_detects_invalid_fk():
    rows = [
        {"company_id": "TCS"},
        {"company_id": "XYZ"},
    ]

    valid_keys = {"TCS", "INFY", "RELIANCE"}

    failures = check_fk_validity(rows, "company_id", valid_keys)

    assert len(failures) == 1
    assert failures[0]["rule_id"] == "DQ-03"
    assert failures[0]["company_id"] == "XYZ"
    assert failures[0]["severity"] == "CRITICAL"


def test_dq03_valid_fk():
    rows = [
        {"company_id": "TCS"},
        {"company_id": "INFY"},
    ]

    valid_keys = {"TCS", "INFY", "RELIANCE"}

    failures = check_fk_validity(rows, "company_id", valid_keys)

    assert failures == []