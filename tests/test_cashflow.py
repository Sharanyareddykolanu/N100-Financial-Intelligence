import pytest

from src.analytics.cashflow import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    classify_capital_allocation,
    capital_allocation_row,
)


def test_free_cash_flow_normal():
    assert free_cash_flow(100, -40) == 60


def test_free_cash_flow_negative_allowed():
    assert free_cash_flow(50, -100) == -50


def test_cfo_quality_high():
    ratio, label = cfo_quality_score(
        [120, 130, 110, 140, 150],
        [100, 100, 100, 100, 100],
    )

    assert ratio == pytest.approx(1.3)
    assert label == "High Quality"


def test_cfo_quality_pat_zero():
    ratio, label = cfo_quality_score(
        [100, 100],
        [0, 0],
    )

    assert ratio is None
    assert label is None


def test_capex_intensity_asset_light():
    value, label = capex_intensity(-20, 1000)

    assert value == pytest.approx(2)
    assert label == "Asset Light"


def test_fcf_conversion_zero_operating_profit():
    assert fcf_conversion_rate(50, 0) is None


def test_high_cfo_pat_shareholder_returns():
    assert classify_capital_allocation(
        150,
        -100,
        -20,
        cfo_pat_ratio=1.5,
    ) == "Shareholder Returns"


def test_capital_allocation_row():
    row = capital_allocation_row(
        "RELIANCE",
        2025,
        100,
        -60,
        20,
    )

    assert row["company_id"] == "RELIANCE"
    assert row["year"] == 2025
    assert row["cfo_sign"] == "+"
    assert row["cfi_sign"] == "-"
    assert row["cff_sign"] == "+"
    assert row["pattern_label"] == "Mixed"
