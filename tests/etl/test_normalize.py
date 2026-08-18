import pytest

from src.normalize import normalize_year, normalize_ticker
from src.loader import load_excel


# ============================================================
# normalize_year() tests
# ============================================================

def test_normalize_year_integer():
    assert normalize_year(2024) == 2024


def test_normalize_year_string():
    assert normalize_year("2024") == 2024


def test_normalize_year_with_spaces():
    assert normalize_year(" 2024 ") == 2024


def test_normalize_year_fy_prefix():
    assert normalize_year("FY2024") == 2024


def test_normalize_year_fy_with_space():
    assert normalize_year("FY 2024") == 2024


def test_normalize_year_range():
    assert normalize_year("2024-25") == 2024


def test_normalize_year_fy_range():
    assert normalize_year("FY2024-25") == 2024


def test_normalize_year_fy_space_range():
    assert normalize_year("FY 2024-25") == 2024


def test_normalize_year_float():
    assert normalize_year(2024.0) == 2024


def test_normalize_year_none():
    assert normalize_year(None) is None


def test_normalize_year_empty():
    assert normalize_year("") is None


def test_normalize_year_spaces_only():
    assert normalize_year("   ") is None


def test_normalize_year_invalid_text():
    assert normalize_year("ABC") is None


def test_normalize_year_invalid_format():
    assert normalize_year("20XX") is None


def test_normalize_year_decimal():
    assert normalize_year(2024.5) is None


def test_normalize_year_nan():
    assert normalize_year(float("nan")) is None


def test_normalize_year_lowercase_fy():
    assert normalize_year("fy2024") == 2024


def test_normalize_year_mixed_text():
    assert normalize_year("Financial Year 2024") == 2024


# ============================================================
# normalize_ticker() tests
# ============================================================

def test_normalize_ticker_uppercase():
    assert normalize_ticker("TCS") == "TCS"


def test_normalize_ticker_lowercase():
    assert normalize_ticker("tcs") == "TCS"


def test_normalize_ticker_mixed_case():
    assert normalize_ticker("TcS") == "TCS"


def test_normalize_ticker_leading_space():
    assert normalize_ticker(" TCS") == "TCS"


def test_normalize_ticker_trailing_space():
    assert normalize_ticker("TCS ") == "TCS"


def test_normalize_ticker_both_spaces():
    assert normalize_ticker(" TCS ") == "TCS"


def test_normalize_ticker_ns():
    assert normalize_ticker("infy.ns") == "INFY.NS"


def test_normalize_ticker_ns_spaces():
    assert normalize_ticker(" infy.ns ") == "INFY.NS"


def test_normalize_ticker_reliance():
    assert normalize_ticker("reliance") == "RELIANCE"


def test_normalize_ticker_multiple_spaces():
    assert normalize_ticker("T  C  S") == "T C S"


def test_normalize_ticker_none():
    assert normalize_ticker(None) is None


def test_normalize_ticker_empty():
    assert normalize_ticker("") is None


def test_normalize_ticker_spaces_only():
    assert normalize_ticker("   ") is None


def test_normalize_ticker_nan():
    assert normalize_ticker(float("nan")) is None


def test_normalize_ticker_number():
    assert normalize_ticker(123) == "123"


def test_normalize_ticker_lowercase_ns():
    assert normalize_ticker("reliance.ns") == "RELIANCE.NS"


def test_normalize_ticker_alphanumeric():
    assert normalize_ticker("ABC123") == "ABC123"


def test_normalize_ticker_special_character():
    assert normalize_ticker("ABC-123") == "ABC-123"
    from src.loader import load_excel


def test_load_excel_missing_file():
    with pytest.raises(FileNotFoundError):
        load_excel("does_not_exist.xlsx")


def test_load_excel_invalid_extension(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("hello")

    with pytest.raises(ValueError):
        load_excel(file)