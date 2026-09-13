from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SUPPORTING_DIR = ROOT / "supporting datasets"


def test_companies_file():
    path = DATA_DIR / "companies.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=1)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_profitandloss_file():
    path = DATA_DIR / "profitandloss.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=1)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_balancesheet_file():
    path = DATA_DIR / "balancesheet.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=1)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_cashflow_file():
    path = DATA_DIR / "cashflow.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=1)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_financial_ratios_file():
    path = SUPPORTING_DIR / "financial_ratios.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=0)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_market_cap_file():
    path = SUPPORTING_DIR / "market_cap.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=0)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_sectors_file():
    path = SUPPORTING_DIR / "sectors.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=0)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_stock_prices_file():
    path = SUPPORTING_DIR / "stock_prices.xlsx"
    assert path.exists()
    df = pd.read_excel(path, header=0)
    assert len(df) > 0
    assert len(df.columns) > 0


def test_companies_required_columns():
    path = DATA_DIR / "companies.xlsx"
    df = pd.read_excel(path, header=1)
    columns = {str(c).strip().lower() for c in df.columns}
    assert any(c in columns for c in ["company_id", "id", "ticker"])


def test_profit_loss_required_columns():
    path = DATA_DIR / "profitandloss.xlsx"
    df = pd.read_excel(path, header=1)
    columns = {str(c).strip().lower() for c in df.columns}
    assert any(c in columns for c in ["year", "financial_year", "fy"])
