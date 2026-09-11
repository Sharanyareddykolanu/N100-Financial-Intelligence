import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"


MARKET_CAP_FILE = (
    PROJECT_ROOT
    / "data"
    / "1788501620397-69ae3e7f-market_cap.xlsx"
)


def load_data():
    with sqlite3.connect(DB_PATH) as conn:

        companies = pd.read_sql_query(
            """
            SELECT
                company_id,
                company_name,
                ticker
            FROM companies
            """,
            conn
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                sector
            FROM company_sector
            """,
            conn
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                free_cash_flow_cr
            FROM financial_ratios
            """,
            conn
        )

    market_cap = pd.read_excel(MARKET_CAP_FILE)

    return companies, sectors, ratios, market_cap


def build_valuation():

    companies, sectors, ratios, market_cap = load_data()

    # ---------------------------------------------------------
    # Latest market data
    # ---------------------------------------------------------

    market_cap["year"] = pd.to_numeric(
        market_cap["year"],
        errors="coerce"
    )

    latest_market_year = market_cap["year"].max()

    market_latest = market_cap[
        market_cap["year"] == latest_market_year
    ].copy()

    # ---------------------------------------------------------
    # Latest FCF
    # ---------------------------------------------------------

    ratios["year"] = pd.to_numeric(
        ratios["year"],
        errors="coerce"
    )

    latest_ratio_year = ratios["year"].max()

    ratios_latest = ratios[
        ratios["year"] == latest_ratio_year
    ].copy()

    # ---------------------------------------------------------
    # Merge company + sector + valuation + FCF
    # ---------------------------------------------------------

    
    result = companies.merge(
    sectors,
    on="company_id",
    how="inner"
)

    result = result.merge(
        market_latest[
            [
                "company_id",
                "pe_ratio",
                "pb_ratio",
                "ev_ebitda",
                "market_cap_crore",
                "dividend_yield_pct"
            ]
        ],
        on="company_id",
        how="left"
    )

    result = result.merge(
        ratios_latest[
            [
                "company_id",
                "free_cash_flow_cr"
            ]
        ],
        on="company_id",
        how="left"
    )

    # ---------------------------------------------------------
    # FCF Yield
    # ---------------------------------------------------------

    result["fcf_yield_pct"] = (
        result["free_cash_flow_cr"]
        / result["market_cap_crore"]
        * 100
    )

    result.loc[
        result["market_cap_crore"] <= 0,
        "fcf_yield_pct"
    ] = pd.NA

    # ---------------------------------------------------------
    # Sector median P/E
    # ---------------------------------------------------------

    result["5yr_median_PE"] = (
        result.groupby("sector")["pe_ratio"]
        .transform("median")
    )

    # ---------------------------------------------------------
    # P/E vs sector median
    # ---------------------------------------------------------

    result["PE_vs_sector_median_pct"] = (
        (
            result["pe_ratio"]
            / result["5yr_median_PE"]
        ) - 1
    ) * 100

    # ---------------------------------------------------------
    # Valuation flags
    # ---------------------------------------------------------

    def valuation_flag(row):

        pe = row["pe_ratio"]
        median = row["5yr_median_PE"]

        if pd.isna(pe) or pd.isna(median) or median <= 0:
            return "N/A"

        if pe > median * 1.5:
            return "Caution"

        if pe < median * 0.7:
            return "Discount"

        return "Fair"

    result["flag"] = result.apply(
        valuation_flag,
        axis=1
    )

    # ---------------------------------------------------------
    # Final columns
    # ---------------------------------------------------------

    output = result[
        [
            "company_id",
            "company_name",
            "ticker",
            "sector",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "fcf_yield_pct",
            "5yr_median_PE",
            "PE_vs_sector_median_pct",
            "flag"
        ]
    ].copy()

    output = output.sort_values(
        ["flag", "company_name"]
    )

    return output


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    valuation = build_valuation()

    # Main Excel output
    excel_path = OUTPUT_DIR / "valuation_summary.xlsx"

    valuation.to_excel(
        excel_path,
        index=False
    )

    # Only Caution + Discount
    flags = valuation[
        valuation["flag"].isin(
            ["Caution", "Discount"]
        )
    ].copy()

    csv_path = OUTPUT_DIR / "valuation_flags.csv"

    flags.to_csv(
        csv_path,
        index=False
    )

    print()
    print("Valuation module completed.")
    print(f"Companies: {len(valuation)}")
    print(f"Caution: {(valuation['flag'] == 'Caution').sum()}")
    print(f"Discount: {(valuation['flag'] == 'Discount').sum()}")
    print(f"Fair: {(valuation['flag'] == 'Fair').sum()}")
    print(f"N/A: {(valuation['flag'] == 'N/A').sum()}")
    print()
    print(f"Created: {excel_path}")
    print(f"Created: {csv_path}")


if __name__ == "__main__":
    main()