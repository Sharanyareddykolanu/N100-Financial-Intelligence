import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "nifty100.db"
OUTPUT_DIR = ROOT / "output"

OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    conn = sqlite3.connect(DB_PATH)

    cashflow = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            operating_cash_flow,
            investing_cash_flow,
            financing_cash_flow,
            free_cash_flow
        FROM company_cashflow
        ORDER BY company_id, year
        """,
        conn,
    )

    profit_loss = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            sales,
            net_profit
        FROM company_profit_loss
        ORDER BY company_id, year
        """,
        conn,
    )

    balance_sheet = pd.read_sql_query(
        """
        SELECT
            company_id,
            year,
            debt
        FROM company_balance_sheet
        ORDER BY company_id, year
        """,
        conn,
    )

    sector = pd.read_sql_query(
        """
        SELECT
            company_id,
            sector
        FROM company_sector
        """,
        conn,
    )

    conn.close()

    return cashflow, profit_loss, balance_sheet, sector


def safe_ratio(numerator, denominator):
    if pd.isna(numerator) or pd.isna(denominator):
        return np.nan

    if denominator == 0:
        return np.nan

    return numerator / denominator


def cfo_quality_label(score):
    if pd.isna(score):
        return "N/A"

    if score > 1.0:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def capex_label(intensity):
    if pd.isna(intensity):
        return "N/A"

    if intensity < 3:
        return "Asset Light"

    if intensity <= 8:
        return "Moderate"

    return "Capital Intensive"


def calculate_cagr(first_value, last_value, years):
    if pd.isna(first_value) or pd.isna(last_value):
        return np.nan

    if years <= 0:
        return np.nan

    if first_value == 0:
        return np.nan

    # CAGR is not meaningful when signs prevent a real-valued result.
    if first_value < 0 or last_value < 0:
        return np.nan

    return ((last_value / first_value) ** (1 / years) - 1) * 100


def calculate_company(company_id, cf, pl, bs, sector):
    cf = cf.sort_values("year").copy()
    pl = pl.sort_values("year").copy()
    bs = bs.sort_values("year").copy()

    sector_value = sector["sector"].iloc[0] if not sector.empty else "Unknown"

    # ---------------------------------------------------------
    # CFO Quality Score
    # Average CFO/PAT over latest 5 available common years
    # ---------------------------------------------------------
    merged = pd.merge(
        cf[["year", "operating_cash_flow"]],
        pl[["year", "net_profit"]],
        on="year",
        how="inner",
    )

    merged["cfo_pat_ratio"] = merged.apply(
        lambda row: safe_ratio(
            row["operating_cash_flow"],
            row["net_profit"],
        ),
        axis=1,
    )

    cfo_5 = merged.dropna(subset=["cfo_pat_ratio"]).tail(5)

    if cfo_5.empty:
        cfo_quality_score = np.nan
    else:
        cfo_quality_score = cfo_5["cfo_pat_ratio"].mean()

    cfo_quality_label_value = cfo_quality_label(cfo_quality_score)

    # ---------------------------------------------------------
    # CapEx Intensity
    # abs(investing activity) / sales * 100
    # Latest common year
    # ---------------------------------------------------------
    capex_data = pd.merge(
        cf[["year", "investing_cash_flow"]],
        pl[["year", "sales"]],
        on="year",
        how="inner",
    ).dropna(subset=["investing_cash_flow", "sales"])

    if capex_data.empty:
        capex_intensity = np.nan
    else:
        latest_capex = capex_data.iloc[-1]
        capex_intensity = safe_ratio(
            abs(latest_capex["investing_cash_flow"]),
            latest_capex["sales"],
        )

        if not pd.isna(capex_intensity):
            capex_intensity *= 100

    capex_label_value = capex_label(capex_intensity)

    # ---------------------------------------------------------
    # FCF CAGR — latest 5 years
    # ---------------------------------------------------------
    fcf_data = cf.dropna(subset=["free_cash_flow"]).sort_values("year")

    if len(fcf_data) >= 5:
        fcf_5 = fcf_data.tail(5)
        first_year = fcf_5.iloc[0]["year"]
        last_year = fcf_5.iloc[-1]["year"]
        years = last_year - first_year

        fcf_cagr = calculate_cagr(
            fcf_5.iloc[0]["free_cash_flow"],
            fcf_5.iloc[-1]["free_cash_flow"],
            years,
        )
    else:
        fcf_cagr = np.nan

    # ---------------------------------------------------------
    # FCF Conversion
    # Latest FCF / CFO * 100
    # ---------------------------------------------------------
    latest_cf = cf.iloc[-1] if not cf.empty else None

    if latest_cf is None:
        fcf_conversion = np.nan
    else:
        fcf_conversion = safe_ratio(
            latest_cf["free_cash_flow"],
            latest_cf["operating_cash_flow"],
        )

        if not pd.isna(fcf_conversion):
            fcf_conversion *= 100

    # ---------------------------------------------------------
    # Distress Signal
    # CFO < 0 AND CFF > 0
    # ---------------------------------------------------------
    distress_flag = False

    if latest_cf is not None:
        distress_flag = (
            pd.notna(latest_cf["operating_cash_flow"])
            and pd.notna(latest_cf["financing_cash_flow"])
            and latest_cf["operating_cash_flow"] < 0
            and latest_cf["financing_cash_flow"] > 0
        )

    # ---------------------------------------------------------
    # Deleveraging
    # CFF < 0 AND borrowings/debt declining YoY
    # ---------------------------------------------------------
    deleveraging_flag = False

    if len(bs) >= 2 and latest_cf is not None:
        latest_bs = bs.iloc[-1]
        previous_bs = bs.iloc[-2]

        debt_declining = (
            pd.notna(latest_bs["debt"])
            and pd.notna(previous_bs["debt"])
            and latest_bs["debt"] < previous_bs["debt"]
        )

        cff_negative = (
            pd.notna(latest_cf["financing_cash_flow"])
            and latest_cf["financing_cash_flow"] < 0
        )

        deleveraging_flag = cff_negative and debt_declining

    # ---------------------------------------------------------
    # Capital Allocation Label
    # ---------------------------------------------------------
    if distress_flag:
        capital_allocation_label = "Distress"
    elif deleveraging_flag:
        capital_allocation_label = "Deleveraging"
    elif capex_label_value == "Capital Intensive":
        capital_allocation_label = "Growth Investment"
    elif capex_label_value == "Asset Light":
        capital_allocation_label = "Asset Light"
    else:
        capital_allocation_label = "Balanced"

    return {
        "company_id": company_id,
        "sector": sector_value,
        "cfo_quality_score": cfo_quality_score,
        "cfo_quality_label": cfo_quality_label_value,
        "capex_intensity_pct": capex_intensity,
        "capex_label": capex_label_value,
        "fcf_cagr_5yr": fcf_cagr,
        "fcf_conversion_pct": fcf_conversion,
        "distress_flag": distress_flag,
        "deleveraging_flag": deleveraging_flag,
        "capital_allocation_label": capital_allocation_label,
    }


def generate_outputs():
    cashflow, profit_loss, balance_sheet, sector = load_data()

    companies = sorted(cashflow["company_id"].dropna().unique())

    results = []

    for company_id in companies:
        cf = cashflow[cashflow["company_id"] == company_id]
        pl = profit_loss[profit_loss["company_id"] == company_id]
        bs = balance_sheet[balance_sheet["company_id"] == company_id]
        sec = sector[sector["company_id"] == company_id]

        result = calculate_company(
            company_id,
            cf,
            pl,
            bs,
            sec,
        )

        results.append(result)

    output = pd.DataFrame(results)

    columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]

    output = output[columns]

    excel_path = OUTPUT_DIR / "cashflow_intelligence.xlsx"

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        output.to_excel(
            writer,
            sheet_name="Cash Flow Intelligence",
            index=False,
        )

    # ---------------------------------------------------------
    # Distress Alerts
    # ---------------------------------------------------------
    distress_ids = output.loc[
        output["distress_flag"] == True,
        "company_id",
    ].tolist()

    alerts = []

    for company_id in distress_ids:
        cf = cashflow[cashflow["company_id"] == company_id].sort_values("year")
        pl = profit_loss[profit_loss["company_id"] == company_id].sort_values("year")

        latest_cf = cf.iloc[-1]
        latest_pl = pl.iloc[-1]

        alerts.append(
            {
                "company_id": company_id,
                "CFO": latest_cf["operating_cash_flow"],
                "CFF": latest_cf["financing_cash_flow"],
                "latest_net_profit": latest_pl["net_profit"],
            }
        )

    alerts_df = pd.DataFrame(
        alerts,
        columns=[
            "company_id",
            "CFO",
            "CFF",
            "latest_net_profit",
        ],
    )

    alerts_path = OUTPUT_DIR / "distress_alerts.csv"
    alerts_df.to_csv(alerts_path, index=False)

    print("=" * 50)
    print("DAY 31 CASH FLOW INTELLIGENCE")
    print("=" * 50)
    print(f"Companies processed       : {len(output)}")
    print(f"High Quality CFO          : {(output['cfo_quality_label'] == 'High Quality').sum()}")
    print(f"Moderate CFO              : {(output['cfo_quality_label'] == 'Moderate').sum()}")
    print(f"Accrual Risk              : {(output['cfo_quality_label'] == 'Accrual Risk').sum()}")
    print(f"Distress companies        : {output['distress_flag'].sum()}")
    print(f"Deleveraging companies    : {output['deleveraging_flag'].sum()}")
    print()
    print(f"Created: {excel_path}")
    print(f"Created: {alerts_path}")
    print("=" * 50)


if __name__ == "__main__":
    generate_outputs()