import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = "nifty100.db"
OUTPUT_PATH = Path("output/pros_cons_generated.csv")

OUTPUT_COLUMNS = [
    "company_id",
    "type",
    "rule_id",
    "text",
    "confidence_pct",
]


# ---------------------------------------------------------
# Confidence helpers
# ---------------------------------------------------------

def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def confidence_above(value, threshold, strong_value):
    """
    Confidence for rules where higher value = stronger signal.
    """
    if pd.isna(value) or value <= threshold:
        return 0

    if strong_value <= threshold:
        return 70

    strength = (value - threshold) / (strong_value - threshold)
    return round(clamp(65 + strength * 35), 2)


def confidence_below(value, threshold, strong_value):
    """
    Confidence for rules where lower value = stronger signal.
    """
    if pd.isna(value) or value >= threshold:
        return 0

    if strong_value >= threshold:
        return 70

    strength = (threshold - value) / (threshold - strong_value)
    return round(clamp(65 + strength * 35), 2)


def sustained_confidence(years, required_years, maximum_years=5):
    """
    Confidence based on how long a condition is sustained.
    """
    if years < required_years:
        return 0

    extra = min(years - required_years, maximum_years - required_years)
    return round(clamp(70 + extra * 7), 2)


def trend_confidence(values, direction):
    """
    Confidence based on a consecutive trend.
    """
    values = [x for x in values if pd.notna(x)]

    if len(values) < 3:
        return 0

    if direction == "up":
        valid = all(values[i] > values[i - 1] for i in range(1, len(values)))
    else:
        valid = all(values[i] < values[i - 1] for i in range(1, len(values)))

    return 80 if valid else 0


# ---------------------------------------------------------
# Data helpers
# ---------------------------------------------------------

def latest_row(df):
    if df.empty:
        return None

    return df.sort_values("year").iloc[-1]


def consecutive_positive(values, count):
    values = list(values)

    if len(values) < count:
        return False

    return all(v > 0 for v in values[-count:])


def consecutive_negative(values, count):
    values = list(values)

    if len(values) < count:
        return False

    return all(v < 0 for v in values[-count:])


def consecutive_decline(values, count):
    values = list(values)

    if len(values) < count + 1:
        return False

    recent = values[-(count + 1):]

    return all(
        recent[i] < recent[i - 1]
        for i in range(1, len(recent))
    )


def consecutive_increase(values, count):
    values = list(values)

    if len(values) < count + 1:
        return False

    recent = values[-(count + 1):]

    return all(
        recent[i] > recent[i - 1]
        for i in range(1, len(recent))
    )


# ---------------------------------------------------------
# Main generator
# ---------------------------------------------------------

def generate_pros_cons():

    conn = sqlite3.connect(DB_PATH)

    companies = pd.read_sql_query(
        "SELECT company_id FROM companies",
        conn,
    )

    ratios = pd.read_sql_query(
        "SELECT * FROM financial_ratios",
        conn,
    )

    pnl = pd.read_sql_query(
        "SELECT * FROM company_profit_loss",
        conn,
    )

    balance = pd.read_sql_query(
        "SELECT * FROM company_balance_sheet",
        conn,
    )

    valuation = pd.read_sql_query(
        "SELECT * FROM company_valuation",
        conn,
    )

    company_ratios = pd.read_sql_query(
        "SELECT * FROM company_ratios",
        conn,
    )

    sectors = pd.read_sql_query(
        "SELECT * FROM company_sector",
        conn,
    )

    conn.close()

    results = []

    for company_id in companies["company_id"]:

        r = ratios[
            ratios["company_id"] == company_id
        ].sort_values("year")

        p = pnl[
            pnl["company_id"] == company_id
        ].sort_values("year")

        b = balance[
            balance["company_id"] == company_id
        ].sort_values("year")

        v = valuation[
            valuation["company_id"] == company_id
        ].sort_values("year")

        cr = company_ratios[
            company_ratios["company_id"] == company_id
        ].sort_values("year")

        sector_rows = sectors[
            sectors["company_id"] == company_id
        ]

        sector = ""
        if not sector_rows.empty:
            sector = str(
                sector_rows.iloc[-1]["sector"]
            ).lower()

        non_financial = not any(
            word in sector
            for word in [
                "financial",
                "bank",
                "insurance",
                "nbfc",
            ]
        )

        if r.empty and p.empty and b.empty:
            continue

        latest_r = latest_row(r)
        latest_p = latest_row(p)
        latest_b = latest_row(b)
        latest_v = latest_row(v)
        latest_cr = latest_row(cr)

        # =================================================
        # PRO RULE 1
        # ROE > 20% sustained for 3+ years
        # =================================================

        if not r.empty:
            roe_values = r["return_on_equity_pct"].dropna().tolist()

            if len(roe_values) >= 3:
                recent = roe_values[-3:]

                if all(x > 20 for x in recent):
                    conf = confidence_above(
                        min(recent),
                        20,
                        35,
                    )

                    if conf > 60:
                        results.append([
                            company_id,
                            "pro",
                            "P1",
                            "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
                            conf,
                        ])

        # =================================================
        # PRO RULE 2
        # FCF positive for 5+ consecutive years
        # =================================================

        if not r.empty:
            fcf = r["free_cash_flow_cr"].dropna().tolist()

            if consecutive_positive(fcf, 5):
                conf = sustained_confidence(
                    5,
                    5,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P2",
                        "Strong free cash flow generation over 5 years signals healthy business fundamentals",
                        conf,
                    ])

        # =================================================
        # PRO RULE 3
        # D/E = 0 latest year
        # =================================================

        if latest_r is not None:
            de = latest_r["debt_to_equity"]

            if pd.notna(de) and de == 0:
                results.append([
                    company_id,
                    "pro",
                    "P3",
                    "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
                    100,
                ])

        # =================================================
        # PRO RULE 4
        # Revenue CAGR > 15%
        # =================================================

        if latest_r is not None:
            revenue_cagr = latest_r["revenue_cagr_5yr"]

            if pd.notna(revenue_cagr) and revenue_cagr > 15:
                conf = confidence_above(
                    revenue_cagr,
                    15,
                    25,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P4",
                        "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
                        conf,
                    ])

        # =================================================
        # PRO RULE 5
        # OPM > 25%
        # =================================================

        if latest_r is not None:
            opm = latest_r["operating_profit_margin_pct"]

            if pd.notna(opm) and opm > 25:
                conf = confidence_above(
                    opm,
                    25,
                    40,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P5",
                        "Operating profit margin above 25% indicates strong pricing power and cost discipline",
                        conf,
                    ])

        # =================================================
        # PRO RULE 6
        # PAT CAGR > 20%
        # =================================================

        if latest_r is not None:
            pat_cagr = latest_r["pat_cagr_5yr"]

            if pd.notna(pat_cagr) and pat_cagr > 20:
                conf = confidence_above(
                    pat_cagr,
                    20,
                    35,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P6",
                        "Net profit compounding at above 20% over 5 years creates significant shareholder value",
                        conf,
                    ])

        # =================================================
        # PRO RULE 7
        # ICR > 10 OR Debt Free
        # =================================================

        if latest_r is not None:
            icr = latest_r["interest_coverage"]
            de = latest_r["debt_to_equity"]

            debt_free = (
                pd.notna(de)
                and de == 0
            )

            if debt_free:
                conf = 100
            elif pd.notna(icr) and icr > 10:
                conf = confidence_above(
                    icr,
                    10,
                    20,
                )
            else:
                conf = 0

            if conf > 60:
                results.append([
                    company_id,
                    "pro",
                    "P7",
                    "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
                    conf,
                ])

        # =================================================
        # PRO RULE 8
        # Dividend yield > 2% + FCF positive
        # =================================================

        if latest_v is not None and latest_r is not None:
            dividend_yield = latest_v["dividend_yield"]
            fcf = latest_r["free_cash_flow_cr"]

            if (
                pd.notna(dividend_yield)
                and dividend_yield > 2
                and pd.notna(fcf)
                and fcf > 0
            ):
                conf = confidence_above(
                    dividend_yield,
                    2,
                    5,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P8",
                        "Consistent dividend yield above 2% backed by positive free cash flow",
                        conf,
                    ])

        # =================================================
        # PRO RULE 9
        # EPS CAGR > 15%
        # =================================================

        if latest_r is not None:
            eps_cagr = latest_r["eps_cagr_5yr"]

            if pd.notna(eps_cagr) and eps_cagr > 15:
                conf = confidence_above(
                    eps_cagr,
                    15,
                    25,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P9",
                        "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
                        conf,
                    ])

        # =================================================
        # PRO RULE 10
        # ROE improving for 3 consecutive years
        # =================================================

        if not r.empty:
            roe_values = r["return_on_equity_pct"].dropna().tolist()

            if consecutive_increase(roe_values, 3):
                conf = trend_confidence(
                    roe_values[-4:],
                    "up",
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P10",
                        "Return on equity improving for 3 consecutive years shows strengthening business quality",
                        conf,
                    ])

        # =================================================
        # PRO RULE 11
        # Revenue CAGR > PAT CAGR
        # =================================================

        if latest_r is not None:
            revenue_cagr = latest_r["revenue_cagr_5yr"]
            pat_cagr = latest_r["pat_cagr_5yr"]

            if (
                pd.notna(revenue_cagr)
                and pd.notna(pat_cagr)
                and revenue_cagr > pat_cagr
            ):
                difference = revenue_cagr - pat_cagr

                conf = confidence_above(
                    difference,
                    0,
                    10,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "pro",
                        "P11",
                        "Revenue growing slower than profits shows improving operating leverage and scale benefits",
                        conf,
                    ])

        # =================================================
        # PRO RULE 12
        # Assets growing + debt declining
        # =================================================

        if len(b) >= 2:
            previous = b.iloc[-2]
            current = b.iloc[-1]

            assets_growing = (
                pd.notna(current["total_assets"])
                and pd.notna(previous["total_assets"])
                and current["total_assets"]
                > previous["total_assets"]
            )

            debt_declining = (
                pd.notna(current["debt"])
                and pd.notna(previous["debt"])
                and current["debt"]
                < previous["debt"]
            )

            if assets_growing and debt_declining:
                results.append([
                    company_id,
                    "pro",
                    "P12",
                    "Growing asset base funded by internal accruals reflects self-sustaining growth",
                    85,
                ])

        # =================================================
        # CON RULE 1
        # D/E > 2 non-financial
        # =================================================

        if latest_r is not None and non_financial:
            de = latest_r["debt_to_equity"]

            if pd.notna(de) and de > 2:
                conf = confidence_above(
                    de,
                    2,
                    4,
                )

                if conf > 60:
                    text = (
                        f"Debt-to-equity ratio of {de:.2f} "
                        "is elevated for a non-financial company and warrants monitoring"
                    )

                    results.append([
                        company_id,
                        "con",
                        "C1",
                        text,
                        conf,
                    ])

        # =================================================
        # CON RULE 2
        # FCF negative for 3 consecutive years
        # =================================================

        if not r.empty:
            fcf = r["free_cash_flow_cr"].dropna().tolist()

            if consecutive_negative(fcf, 3):
                results.append([
                    company_id,
                    "con",
                    "C2",
                    "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
                    85,
                ])

        # =================================================
        # CON RULE 3
        # OPM declining 3 consecutive years
        # =================================================

        if not r.empty:
            opm_values = r["operating_profit_margin_pct"].dropna().tolist()

            if consecutive_decline(opm_values, 3):
                results.append([
                    company_id,
                    "con",
                    "C3",
                    "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
                    85,
                ])

        # =================================================
        # CON RULE 4
        # Net profit negative latest year
        # =================================================

        if latest_p is not None:
            net_profit = latest_p["net_profit"]

            if pd.notna(net_profit) and net_profit < 0:
                results.append([
                    company_id,
                    "con",
                    "C4",
                    "Company reported a net loss in the most recent financial year",
                    100,
                ])

        # =================================================
        # CON RULE 5
        # Revenue declining for 2+ years
        # =================================================

        if not p.empty:
            sales = p["sales"].dropna().tolist()

            if consecutive_decline(sales, 2):
                results.append([
                    company_id,
                    "con",
                    "C5",
                    "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
                    85,
                ])

        # =================================================
        # CON RULE 6
        # ICR < 1.5
        # =================================================

        if latest_r is not None:
            icr = latest_r["interest_coverage"]

            if pd.notna(icr) and icr < 1.5:
                conf = confidence_below(
                    icr,
                    1.5,
                    0.5,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "con",
                        "C6",
                        "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
                        conf,
                    ])

        # =================================================
        # CON RULE 7
        # Dividend payout > 100%
        # =================================================

        if latest_r is not None:
            payout = latest_r["dividend_payout_ratio_pct"]

            if pd.notna(payout) and payout > 100:
                conf = confidence_above(
                    payout,
                    100,
                    150,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "con",
                        "C7",
                        "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
                        conf,
                    ])

        # =================================================
        # CON RULE 8
        # D/E rising for 3 consecutive years
        # =================================================

        if not r.empty:
            de_values = r["debt_to_equity"].dropna().tolist()

            if consecutive_increase(de_values, 3):
                results.append([
                    company_id,
                    "con",
                    "C8",
                    "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
                    85,
                ])

        # =================================================
        # CON RULE 9
        # EPS declining 3 consecutive years
        # =================================================

        if not p.empty:
            eps_values = p["eps"].dropna().tolist()

            if consecutive_decline(eps_values, 3):
                results.append([
                    company_id,
                    "con",
                    "C9",
                    "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
                    85,
                ])

        # =================================================
        # CON RULE 10
        # ROCE < 10%
        #
        # ROCE = Operating Profit / Capital Employed * 100
        # Capital Employed = Total Assets - Total Liabilities
        # =================================================

        if latest_p is not None and latest_b is not None:

            operating_profit = latest_p["operating_profit"]

            capital_employed = (
                latest_b["total_assets"]
                - latest_b["total_liabilities"]
            )

            if (
                pd.notna(operating_profit)
                and pd.notna(capital_employed)
                and capital_employed > 0
            ):
                roce = (
                    operating_profit
                    / capital_employed
                    * 100
                )

                if roce < 10:
                    conf = confidence_below(
                        roce,
                        10,
                        0,
                    )

                    if conf > 60:
                        results.append([
                            company_id,
                            "con",
                            "C10",
                            "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
                            conf,
                        ])

        # =================================================
        # CON RULE 11
        # Net Debt > 3x EBITDA
        #
        # EBITDA proxy:
        # operating_profit
        # =================================================

        if latest_b is not None and latest_p is not None:

            debt = latest_b["debt"]
            cash = latest_b["cash"]
            operating_profit = latest_p["operating_profit"]

            if (
                pd.notna(debt)
                and pd.notna(cash)
                and pd.notna(operating_profit)
                and operating_profit > 0
            ):
                net_debt = debt - cash
                ebitda_proxy = operating_profit

                if net_debt > 3 * ebitda_proxy:
                    leverage = net_debt / ebitda_proxy

                    conf = confidence_above(
                        leverage,
                        3,
                        6,
                    )

                    if conf > 60:
                        results.append([
                            company_id,
                            "con",
                            "C11",
                            "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
                            conf,
                        ])

        # =================================================
        # CON RULE 12
        # Revenue CAGR < 5%
        # =================================================

        if latest_r is not None:
            revenue_cagr = latest_r["revenue_cagr_5yr"]

            if pd.notna(revenue_cagr) and revenue_cagr < 5:
                conf = confidence_below(
                    revenue_cagr,
                    5,
                    0,
                )

                if conf > 60:
                    results.append([
                        company_id,
                        "con",
                        "C12",
                        "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
                        conf,
                    ])

    # -----------------------------------------------------
    # Create output
    # -----------------------------------------------------

    output = pd.DataFrame(
        results,
        columns=OUTPUT_COLUMNS,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    return output, companies


# ---------------------------------------------------------
# Verification
# ---------------------------------------------------------

def verify_coverage(output, companies):

    company_ids = set(
        companies["company_id"]
    )

    pro_ids = set(
        output.loc[
            output["type"] == "pro",
            "company_id",
        ]
    )

    con_ids = set(
        output.loc[
            output["type"] == "con",
            "company_id",
        ]
    )

    # Companies with no generated signal at all
    signal_ids = pro_ids | con_ids
    no_signal = sorted(company_ids - signal_ids)

    # Companies with neither signal because financial data is unavailable
    conn = sqlite3.connect(DB_PATH)

    ratios_check = pd.read_sql_query(
        "SELECT DISTINCT company_id FROM financial_ratios",
        conn,
    )

    conn.close()

    ratio_ids = set(
        ratios_check["company_id"]
    )

    insufficient_data = sorted(
        set(no_signal) - ratio_ids
    )

    # Companies with financial data but no rule triggered
    no_triggered_rule = sorted(
        set(no_signal) & ratio_ids
    )

    # Confidence validation
    low_confidence = output[
        output["confidence_pct"] <= 60
    ]

    print("\n========================================")
    print("DAY 30 PROS/CONS GENERATOR")
    print("========================================")

    print(
        f"Companies in companies table : "
        f"{len(company_ids)}"
    )

    print(
        f"Generated rows                : "
        f"{len(output)}"
    )

    print(
        f"Pro rows                      : "
        f"{(output['type'] == 'pro').sum()}"
    )

    print(
        f"Con rows                      : "
        f"{(output['type'] == 'con').sum()}"
    )

    print("\n----------------------------------------")
    print("SIGNAL COVERAGE")
    print("----------------------------------------")

    print(
        f"Companies with >=1 Pro        : "
        f"{len(pro_ids)}"
    )

    print(
        f"Companies with >=1 Con        : "
        f"{len(con_ids)}"
    )

    print(
        f"Companies with any signal     : "
        f"{len(signal_ids)}"
    )

    print(
        f"Companies with no signal      : "
        f"{len(no_signal)}"
    )

    print("\n----------------------------------------")
    print("NO-SIGNAL COMPANIES")
    print("----------------------------------------")

    if no_signal:
        for company_id in no_signal:
            print(f"- {company_id}")
    else:
        print("None")

    print("\n----------------------------------------")
    print("INSUFFICIENT DATA")
    print("----------------------------------------")

    if insufficient_data:
        for company_id in insufficient_data:
            print(f"- {company_id}")
    else:
        print("None")

    print("\n----------------------------------------")
    print("NO RULE TRIGGERED")
    print("----------------------------------------")

    if no_triggered_rule:
        for company_id in no_triggered_rule:
            print(f"- {company_id}")
    else:
        print("None")

    print("\n----------------------------------------")
    print("CONFIDENCE VALIDATION")
    print("----------------------------------------")

    print(
        f"Rows with confidence > 60% : "
        f"{(output['confidence_pct'] > 60).sum()}"
    )

    print(
        f"Rows with confidence <= 60%: "
        f"{len(low_confidence)}"
    )

    print("\n----------------------------------------")
    print("RULE VALIDATION")
    print("----------------------------------------")

    valid_pro_rules = {
        f"P{i}" for i in range(1, 13)
    }

    valid_con_rules = {
        f"C{i}" for i in range(1, 13)
    }

    valid_rules = valid_pro_rules | valid_con_rules

    invalid_rules = sorted(
        set(output["rule_id"]) - valid_rules
    )

    if invalid_rules:
        print(
            "Invalid rule IDs found:",
            invalid_rules
        )
    else:
        print(
            "All generated rows use the "
            "specified 24 rules."
        )

    print("\n----------------------------------------")
    print("OUTPUT")
    print("----------------------------------------")

    print(OUTPUT_PATH)

    print("\n========================================")

    if invalid_rules:
        print(
            "STATUS: FAILED - invalid rule IDs."
        )
    elif len(low_confidence) > 0:
        print(
            "STATUS: FAILED - confidence threshold violation."
        )
    else:
        print(
            "STATUS: PASSED - rule-based signals "
            "and confidence validation completed."
        )

    print("========================================")


if __name__ == "__main__":

    output, companies = generate_pros_cons()

    verify_coverage(
        output,
        companies,
    )