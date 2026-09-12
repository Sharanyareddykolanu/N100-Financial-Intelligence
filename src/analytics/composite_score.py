import numpy as np
import pandas as pd


def winsorize_scale(series):
    """
    Winsorise values at P10/P90 and scale to 0-100.
    Higher values receive higher scores.
    """
    s = pd.to_numeric(series, errors="coerce")

    if s.notna().sum() == 0:
        return pd.Series(np.nan, index=s.index)

    p10 = s.quantile(0.10)
    p90 = s.quantile(0.90)

    clipped = s.clip(lower=p10, upper=p90)

    if p90 == p10:
        return pd.Series(50.0, index=s.index)

    return ((clipped - p10) / (p90 - p10) * 100).clip(0, 100)


def reverse_score(series):
    """
    Lower values are better.
    Used for Debt-to-Equity.
    """
    return 100 - winsorize_scale(series)


def calculate_roce(df):
    """
    ROCE = Operating Profit / (Equity + Debt) * 100
    """
    denominator = df["total_equity"] + df["debt"]

    return np.where(
        denominator > 0,
        (df["operating_profit"] / denominator) * 100,
        np.nan,
    )


def calculate_fcf_cagr_5yr(df):
    """
    Calculate 5-year FCF CAGR.

    CAGR is calculated only when both current
    and 5-years-prior FCF are positive.
    """
    data = df.sort_values(
        ["company_id", "year"]
    ).copy()

    previous_fcf = (
        data.groupby("company_id")[
            "free_cash_flow_cr"
        ].shift(5)
    )

    current_fcf = data["free_cash_flow_cr"]

    data["fcf_cagr_5yr"] = np.where(
        (current_fcf > 0)
        & (previous_fcf > 0),
        (
            (current_fcf / previous_fcf) ** (1 / 5)
            - 1
        ) * 100,
        np.nan,
    )

    return data


def sector_score(df, column, reverse=False):
    """
    Perform P10/P90 normalisation within sector.

    If sector is missing, use global normalisation
    for those rows.

    Missing metric values receive a neutral score
    of 50 so they do not make the entire composite
    score NULL.
    """
    result = pd.Series(
        np.nan,
        index=df.index,
        dtype=float,
    )

    valid_sector = df["sector"].notna()

    if valid_sector.any():
        result.loc[valid_sector] = (
            df.loc[valid_sector]
            .groupby("sector")[column]
            .transform(
                reverse_score
                if reverse
                else winsorize_scale
            )
        )

    missing_sector = ~valid_sector

    if missing_sector.any():
        result.loc[missing_sector] = (
            reverse_score(df.loc[missing_sector, column])
            if reverse
            else winsorize_scale(
                df.loc[missing_sector, column]
            )
        )

    # Missing metric = neutral contribution.
    result = result.fillna(50.0)

    return result.clip(0, 100)


def calculate_composite_score(df):
    """
    Calculate Day 17 sector-relative composite score.

    Profitability: 35%
        ROE 15%
        ROCE 10%
        NPM 10%

    Cash Quality: 30%
        FCF CAGR 15%
        CFO/PAT 10%
        FCF positive flag 5%

    Growth: 20%
        Revenue CAGR 5Y 10%
        PAT CAGR 5Y 10%

    Leverage: 15%
        D/E score 10%
        ICR score 5%

    Continuous metrics use P10/P90 winsorisation
    and 0-100 scaling within sector.
    """

    data = df.copy()

    # ---------------------------------------------------------
    # Raw metrics
    # ---------------------------------------------------------

    data["roce_pct"] = calculate_roce(data)

    data = calculate_fcf_cagr_5yr(data)

    data["cfo_pat_ratio"] = np.where(
        data["net_profit"] != 0,
        (
            data["cash_from_operations_cr"]
            / data["net_profit"]
        ) * 100,
        np.nan,
    )

    # FCF positive flag
    data["fcf_positive_flag"] = np.where(
        data["free_cash_flow_cr"] > 0,
        100.0,
        0.0,
    )

    # ---------------------------------------------------------
    # Sector-relative scores
    # ---------------------------------------------------------

    data["roe_pct_score"] = sector_score(
        data,
        "return_on_equity_pct",
    )

    data["roce_pct_score"] = sector_score(
        data,
        "roce_pct",
    )

    data["npm_pct_score"] = sector_score(
        data,
        "net_profit_margin_pct",
    )

    data["fcf_cagr_5yr_score"] = sector_score(
        data,
        "fcf_cagr_5yr",
    )

    data["cfo_pat_ratio_score"] = sector_score(
        data,
        "cfo_pat_ratio",
    )

    data["revenue_cagr_5yr_score"] = sector_score(
        data,
        "revenue_cagr_5yr",
    )

    data["pat_cagr_5yr_score"] = sector_score(
        data,
        "pat_cagr_5yr",
    )

    # Lower D/E is better.
    data["debt_to_equity_score"] = sector_score(
        data,
        "debt_to_equity",
        reverse=True,
    )

    # ---------------------------------------------------------
    # ICR
    # ---------------------------------------------------------
    #
    # Project convention:
    # NULL ICR = Debt Free.
    #
    # Since ALL ICR values are NULL in the database,
    # assign the maximum score of 100.
    #
    # This avoids using infinity in percentile
    # calculations.

    if data["interest_coverage"].notna().any():

        data["icr_for_score_score"] = sector_score(
            data,
            "interest_coverage",
        )

        data.loc[
            data["interest_coverage"].isna(),
            "icr_for_score_score",
        ] = 100.0

    else:
        data["icr_for_score_score"] = 100.0

    # FCF positive flag is already 0 or 100.
    data["fcf_positive_flag_score"] = (
        data["fcf_positive_flag"]
    )

    # ---------------------------------------------------------
    # Weighted composite score
    # ---------------------------------------------------------

    data["composite_score"] = (
        data["roe_pct_score"] * 0.15
        + data["roce_pct_score"] * 0.10
        + data["npm_pct_score"] * 0.10
        + data["fcf_cagr_5yr_score"] * 0.15
        + data["cfo_pat_ratio_score"] * 0.10
        + data["fcf_positive_flag_score"] * 0.05
        + data["revenue_cagr_5yr_score"] * 0.10
        + data["pat_cagr_5yr_score"] * 0.10
        + data["debt_to_equity_score"] * 0.10
        + data["icr_for_score_score"] * 0.05
    )

    # Required 0-100 scale.
    data["composite_score"] = (
        data["composite_score"]
        .clip(0, 100)
        .round(2)
    )

    return data