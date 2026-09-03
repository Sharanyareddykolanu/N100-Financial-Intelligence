from pathlib import Path

import pandas as pd
import sqlite3
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "nifty100.db"
CONFIG_PATH = PROJECT_ROOT / "screener_config.yaml"


def load_config():
    """Load screener thresholds from screener_config.yaml."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_screener_data():
    """Load financial ratios plus metrics required by the screener."""
    query = """
        SELECT
            fr.*,
            pl.sales,
            pl.net_profit,
            cv.market_cap,
            cv.pe_ratio,
            cv.pb_ratio,
            cv.dividend_yield,
            c.company_name,
            c.ticker,
            c.sector
        FROM financial_ratios fr

        LEFT JOIN company_profit_loss pl
            ON fr.company_id = pl.company_id
            AND fr.year = pl.year

        LEFT JOIN company_valuation cv
            ON fr.company_id = cv.company_id
            AND fr.year = cv.year

        LEFT JOIN companies c
            ON fr.company_id = c.company_id
    """

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


def apply_filters(df, config):
    """Apply all configured screener filters."""
    filters = config["filters"]
    result = df.copy()

    # ROE minimum
    result = result[
        result["return_on_equity_pct"].notna()
        & (result["return_on_equity_pct"] >= filters["roe_min"])
    ]

    # D/E maximum
    # Financial sector companies are skipped from this filter.
    if filters.get("de_max") is not None:
        non_financial = (
            result["sector"].fillna("").str.lower() != "financials"
        )

        result = result[
            ~non_financial
            | (
                result["debt_to_equity"].notna()
                & (result["debt_to_equity"] <= filters["de_max"])
            )
        ]

    # FCF minimum
    result = result[
        result["free_cash_flow_cr"].notna()
        & (result["free_cash_flow_cr"] >= filters["fcf_min"])
    ]

    # Revenue CAGR 5-year minimum
    result = result[
        result["revenue_cagr_5yr"].notna()
        & (result["revenue_cagr_5yr"] >= filters["revenue_cagr_5yr_min"])
    ]

    # PAT CAGR 5-year minimum
    result = result[
        result["pat_cagr_5yr"].notna()
        & (result["pat_cagr_5yr"] >= filters["pat_cagr_5yr_min"])
    ]

    # OPM minimum
    result = result[
        result["operating_profit_margin_pct"].notna()
        & (
            result["operating_profit_margin_pct"]
            >= filters["opm_min"]
        )
    ]

    # P/E maximum
    result = result[
        result["pe_ratio"].notna()
        & (result["pe_ratio"] <= filters["pe_max"])
    ]

    # P/B maximum
    result = result[
        result["pb_ratio"].notna()
        & (result["pb_ratio"] <= filters["pb_max"])
    ]

    # Dividend Yield minimum
    result = result[
        result["dividend_yield"].notna()
        & (result["dividend_yield"] >= filters["dividend_yield_min"])
    ]
	    # ICR minimum
    # Project convention:
    # NULL ICR means "Debt Free", so treat it as infinity.
    if filters.get("icr_min") is not None:
        icr = result["interest_coverage"].copy()

        debt_free = icr.isna()
        icr.loc[debt_free] = float("inf")

        result = result[
            icr >= filters["icr_min"]
        ]
    # Market Cap minimum
    result = result[
        result["market_cap"].notna()
        & (result["market_cap"] >= filters["market_cap_min"])
    ]

    # Net Profit minimum
    result = result[
        result["net_profit"].notna()
        & (result["net_profit"] >= filters["net_profit_min"])
    ]

    # EPS CAGR minimum
    result = result[
        result["eps_cagr_5yr"].notna()
        & (result["eps_cagr_5yr"] >= filters["eps_cagr_min"])
    ]

    # Asset Turnover minimum
    result = result[
        result["asset_turnover"].notna()
        & (result["asset_turnover"] >= filters["asset_turnover_min"])
    ]

    # Sales minimum
    result = result[
        result["sales"].notna()
        & (result["sales"] >= filters["sales_min"])
    ]

    # Ensure composite quality score is present.
    if "composite_quality_score" not in result.columns:
        result["composite_quality_score"] = pd.NA

    # Sort final results.
    sort_by = config.get("sort_by", "composite_quality_score")
    sort_order = config.get("sort_order", "descending")

    result = result.sort_values(
        by=sort_by,
        ascending=(sort_order.lower() == "ascending"),
        na_position="last",
    )

    return result.reset_index(drop=True)


def run_screener():
    """Run the complete screener pipeline."""
    config = load_config()
    data = load_screener_data()
    filtered = apply_filters(data, config)

    return filtered


if __name__ == "__main__":
    result = run_screener()

    print("=" * 60)
    print("NIFTY 100 SCREENER")
    print("=" * 60)
    print(f"Companies/rows after filtering: {len(result)}")

    if not result.empty:
        columns = [
            "company_id",
            "company_name",
            "ticker",
            "sector",
            "year",
            "return_on_equity_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "operating_profit_margin_pct",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield",
            "market_cap",
            "net_profit",
            "eps_cagr_5yr",
            "asset_turnover",
            "sales",
            "composite_quality_score",
        ]

        available_columns = [
            col for col in columns if col in result.columns
        ]

        print(result[available_columns].head(20).to_string(index=False))
    else:
        print("No companies passed all configured filters.")