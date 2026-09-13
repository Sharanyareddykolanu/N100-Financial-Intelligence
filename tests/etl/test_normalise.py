import math
from src.etl.normaliser import normalize_year


def test_none():
    assert normalize_year(None) is None


def test_integer_year():
    assert normalize_year(2024) == 2024


def test_float_integer_year():
    assert normalize_year(2024.0) == 2024


def test_float_non_integer():
    assert normalize_year(2024.5) is None


def test_nan():
    assert normalize_year(float("nan")) is None


def test_string_year():
    assert normalize_year("2024") == 2024


def test_string_with_spaces():
    assert normalize_year(" 2024 ") == 2024


def test_fy_year():
    assert normalize_year("FY2024") == 2024


def test_fy_year_with_space():
    assert normalize_year("FY 2024") == 2024


def test_financial_year():
    assert normalize_year("2024-25") == 2024


def test_month_year():
    assert normalize_year("Dec 2012") == 2012


def test_month_year_with_hyphen():
    assert normalize_year("Mar-13") == 2013


def test_month_year_with_space():
    assert normalize_year("Mar 13") == 2013


def test_two_digit_year_29():
    assert normalize_year("Mar-29") == 2029


def test_two_digit_year_30():
    assert normalize_year("Mar-30") == 1930


def test_two_digit_year_99():
    assert normalize_year("Dec-99") == 1999


def test_lowercase_fy():
    assert normalize_year("fy2024") == 2024


def test_empty_string():
    assert normalize_year("") is None


def test_invalid_string():
    assert normalize_year("hello") is None


def test_whitespace_string():
    assert normalize_year("   ") is None
