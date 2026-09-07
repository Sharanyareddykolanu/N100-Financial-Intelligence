import pandas as pd


def quality_compounder(df):
    """ROE > 15%, D/E < 1.0, FCF > 0, Revenue CAGR 5Y > 10%."""
    return df[
        (df["return_on_equity_pct"] > 15)
        & (df["debt_to_equity"] < 1.0)
        & (df["free_cash_flow_cr"] > 0)
        & (df["revenue_cagr_5yr"] > 10)
    ].copy()


def value_pick(df):
    """P/E < 20, P/B < 3.0, D/E < 2.0, Dividend Yield > 1%."""
    return df[
        (df["pe_ratio"] < 20)
        & (df["pb_ratio"] < 3.0)
        & (df["debt_to_equity"] < 2.0)
        & (df["dividend_yield"] > 1)
    ].copy()


def growth_accelerator(df):
    """PAT CAGR 5Y > 20%, Revenue CAGR 5Y > 15%, D/E < 2.0."""
    return df[
        (df["pat_cagr_5yr"] > 20)
        & (df["revenue_cagr_5yr"] > 15)
        & (df["debt_to_equity"] < 2.0)
    ].copy()


def dividend_champion(df):
    """Dividend Yield > 2%, Dividend Payout < 80%, FCF > 0."""
    return df[
        (df["dividend_yield"] > 2)
        & (df["dividend_payout_ratio_pct"] < 80)
        & (df["free_cash_flow_cr"] > 0)
    ].copy()


def debt_free_blue_chip(df):
    """D/E = 0, ROE > 12%, Revenue/Sales > 5000 Crore."""
    return df[
        (df["debt_to_equity"] == 0)
        & (df["return_on_equity_pct"] > 12)
        & (df["sales"] > 5000)
    ].copy()


def turnaround_watch(df):
    """
    Revenue CAGR 3Y > 10%, latest FCF > 0,
    and D/E declining year-over-year.
    """
    data = df.sort_values(["company_id", "year"]).copy()

    data["revenue_cagr_3yr"] = (
        data.groupby("company_id")["sales"]
        .transform(
            lambda s: ((s / s.shift(3)) ** (1 / 3) - 1) * 100
        )
    )

    data["previous_de"] = (
        data.groupby("company_id")["debt_to_equity"]
        .shift(1)
    )

    latest = data.sort_values("year").groupby(
        "company_id", as_index=False
    ).tail(1)

    return latest[
        (latest["revenue_cagr_3yr"] > 10)
        & (latest["free_cash_flow_cr"] > 0)
        & latest["previous_de"].notna()
        & (latest["debt_to_equity"] < latest["previous_de"])
    ].copy()


PRESETS = {
    "Quality Compounder": quality_compounder,
    "Value Pick": value_pick,
    "Growth Accelerator": growth_accelerator,
    "Dividend Champion": dividend_champion,
    "Debt-Free Blue Chip": debt_free_blue_chip,
    "Turnaround Watch": turnaround_watch,
}