from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "radar_charts"


AXES = [
    "ROE",
    "ROCE",
    "NPM",
    "D/E",
    "FCF Score",
    "PAT CAGR 5yr",
    "Revenue CAGR 5yr",
    "Composite Score",
]

METRIC_MAP = {
    "ROE": "ROE",
    "ROCE": "ROCE",
    "NPM": "Net Profit Margin",
    "D/E": "D/E",
    "FCF Score": "FCF",
    "PAT CAGR 5yr": "PAT CAGR 5yr",
    "Revenue CAGR 5yr": "Revenue CAGR 5yr",
}


def load_peer_data():
    """Load peer percentile data from SQLite."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year
        FROM peer_percentiles
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def load_composite_scores():
    """Load composite scores and calculate the latest score per company."""
    conn = sqlite3.connect(DB_PATH)

    # Composite scores are stored in financial_ratios.
    query = """
        SELECT
            company_id,
            year,
            composite_quality_score
        FROM financial_ratios
        WHERE composite_quality_score IS NOT NULL
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(
            columns=["company_id", "year", "composite_quality_score"]
        )

    df = df.sort_values(["company_id", "year"])

    return df.groupby("company_id", as_index=False).tail(1)


def load_all_financial_data():
    """Load financial ratios for standalone Nifty 100 reference charts."""
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            company_id,
            year,
            return_on_equity_pct,
            net_profit_margin_pct,
            debt_to_equity,
            free_cash_flow_cr,
            pat_cagr_5yr,
            revenue_cagr_5yr,
            asset_turnover
        FROM financial_ratios
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def latest_peer_rows(peer_df):
    """Get the latest available year for every company/metric."""
    if peer_df.empty:
        return peer_df.copy()

    data = peer_df.sort_values(
        ["company_id", "metric", "year"]
    ).copy()

    return data.groupby(
        ["company_id", "metric"],
        as_index=False,
    ).tail(1)


def get_company_values(company_id, peer_df, composite_df):
    """Return the eight radar-axis values for one company."""
    values = {}

    company_peer = peer_df[
        peer_df["company_id"] == company_id
    ]

    for axis, metric in METRIC_MAP.items():
        rows = company_peer[
            company_peer["metric"] == metric
        ]

        if rows.empty:
            values[axis] = np.nan
        else:
            rows = rows.sort_values("year")
            percentile = rows.iloc[-1]["percentile_rank"]

            if pd.isna(percentile):
                values[axis] = np.nan
            else:
                values[axis] = float(percentile) * 100

    composite = composite_df[
        composite_df["company_id"] == company_id
    ]

    if composite.empty:
        values["Composite Score"] = np.nan
    else:
        score = composite.iloc[-1]["composite_quality_score"]

        if pd.isna(score):
            values["Composite Score"] = np.nan
        else:
            values["Composite Score"] = float(score)

    return values


def calculate_peer_average(company_id, peer_group_name, peer_df, composite_df):
    """Calculate the peer-group average for the radar chart."""
    group_df = peer_df[
        peer_df["peer_group_name"] == peer_group_name
    ].copy()

    group_df = latest_peer_rows(group_df)

    averages = {}

    for axis, metric in METRIC_MAP.items():
        rows = group_df[
            group_df["metric"] == metric
        ]

        if rows.empty:
            averages[axis] = np.nan
        else:
            averages[axis] = (
                pd.to_numeric(
                    rows["percentile_rank"],
                    errors="coerce",
                )
                .mean()
                * 100
            )

    peer_companies = group_df["company_id"].unique()

    peer_scores = composite_df[
        composite_df["company_id"].isin(peer_companies)
    ]["composite_quality_score"]

    averages["Composite Score"] = pd.to_numeric(
        peer_scores,
        errors="coerce",
    ).mean()

    return averages


def normalize_values(values):
    """Replace unavailable metrics with a neutral 50 for plotting."""
    return [
        50.0 if pd.isna(values.get(axis)) else float(values[axis])
        for axis in AXES
    ]


def create_radar_chart(
    company_id,
    values,
    reference_values,
    reference_label,
    output_path,
    title,
):
    """Create and save a readable radar/polar chart."""
    company_values = normalize_values(values)
    reference_values = normalize_values(reference_values)

    angles = np.linspace(
        0,
        2 * np.pi,
        len(AXES),
        endpoint=False,
    ).tolist()

    company_values += company_values[:1]
    reference_values += reference_values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(
        figsize=(9, 9),
        subplot_kw={"projection": "polar"},
    )

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(
        AXES,
        fontsize=11,
    )

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(
        ["20", "40", "60", "80", "100"],
        fontsize=9,
    )

    ax.plot(
        angles,
        company_values,
        linewidth=2.5,
        label=company_id,
    )

    ax.fill(
        angles,
        company_values,
        alpha=0.20,
    )

    ax.plot(
        angles,
        reference_values,
        linestyle="--",
        linewidth=2,
        label=reference_label,
    )

    ax.set_title(
        title,
        fontsize=15,
        fontweight="bold",
        pad=25,
    )

    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.25, 1.10),
        fontsize=10,
    )

    ax.grid(True, alpha=0.4)

    fig.tight_layout()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)


def create_peer_group_charts(
    peer_df,
    composite_df,
):
    """Create one radar chart for every peer-assigned company."""
    companies = (
        peer_df[
            ["company_id", "peer_group_name"]
        ]
        .drop_duplicates()
        .sort_values(["peer_group_name", "company_id"])
    )

    count = 0

    for _, row in companies.iterrows():
        company_id = row["company_id"]
        peer_group = row["peer_group_name"]

        company_values = get_company_values(
            company_id,
            peer_df,
            composite_df,
        )

        peer_average = calculate_peer_average(
            company_id,
            peer_group,
            peer_df,
            composite_df,
        )

        output_path = (
            OUTPUT_DIR
            / f"{company_id}_radar.png"
        )

        create_radar_chart(
            company_id=company_id,
            values=company_values,
            reference_values=peer_average,
            reference_label=f"{peer_group} Average",
            output_path=output_path,
            title=f"{company_id} — {peer_group}",
        )

        count += 1

    return count


def calculate_nifty100_average(
    company_id,
    financial_df,
    composite_df,
):
    """Calculate Nifty 100 average reference values."""
    latest_financial = (
        financial_df
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    reference = {}

    reference["ROE"] = pd.to_numeric(
        latest_financial["return_on_equity_pct"],
        errors="coerce",
    ).mean()

    reference["ROCE"] = 50.0

    reference["NPM"] = pd.to_numeric(
        latest_financial["net_profit_margin_pct"],
        errors="coerce",
    ).mean()

    de_values = pd.to_numeric(
        latest_financial["debt_to_equity"],
        errors="coerce",
    )

    reference["D/E"] = de_values.mean()

    reference["FCF Score"] = 50.0

    reference["PAT CAGR 5yr"] = pd.to_numeric(
        latest_financial["pat_cagr_5yr"],
        errors="coerce",
    ).mean()

    reference["Revenue CAGR 5yr"] = pd.to_numeric(
        latest_financial["revenue_cagr_5yr"],
        errors="coerce",
    ).mean()

    reference["Composite Score"] = pd.to_numeric(
        composite_df["composite_quality_score"],
        errors="coerce",
    ).mean()

    return reference


def create_standalone_charts(
    peer_df,
    financial_df,
    composite_df,
):
    """Create standalone charts for companies without peer groups."""
    all_companies = set(
        financial_df["company_id"].dropna().unique()
    )

    peer_companies = set(
        peer_df["company_id"].dropna().unique()
    )

    unassigned = sorted(
        all_companies - peer_companies
    )

    nifty_average = calculate_nifty100_average(
        None,
        financial_df,
        composite_df,
    )

    count = 0

    for company_id in unassigned:
        composite = composite_df[
            composite_df["company_id"] == company_id
        ]

        if composite.empty:
            company_score = np.nan
        else:
            company_score = composite.iloc[-1][
                "composite_quality_score"
            ]

        company_values = {
            "ROE": np.nan,
            "ROCE": np.nan,
            "NPM": np.nan,
            "D/E": np.nan,
            "FCF Score": np.nan,
            "PAT CAGR 5yr": np.nan,
            "Revenue CAGR 5yr": np.nan,
            "Composite Score": company_score,
        }

        # Standalone charts focus on the available
        # Composite Score against the Nifty 100 average.
        reference_values = {
            axis: 50.0
            for axis in AXES
        }

        reference_values["Composite Score"] = (
            nifty_average["Composite Score"]
        )

        output_path = (
            OUTPUT_DIR
            / f"{company_id}_radar.png"
        )

        create_radar_chart(
            company_id=company_id,
            values=company_values,
            reference_values=reference_values,
            reference_label="Nifty 100 Average",
            output_path=output_path,
            title=f"{company_id} — Standalone",
        )

        count += 1

    return count


def main():
    print("=" * 70)
    print("DAY 19 - RADAR CHART GENERATION")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nLoading peer percentile data...")
    peer_df = load_peer_data()

    print(f"Peer percentile rows: {len(peer_df)}")
    print(
        f"Peer companies: "
        f"{peer_df['company_id'].nunique()}"
    )
    print(
        f"Peer groups: "
        f"{peer_df['peer_group_name'].nunique()}"
    )

    print("\nLoading composite scores...")
    composite_df = load_composite_scores()

    print(
        f"Composite scores: "
        f"{len(composite_df)}"
    )

    print("\nLoading financial data...")
    financial_df = load_all_financial_data()

    print(
        f"Financial rows: "
        f"{len(financial_df)}"
    )
    print(
        f"Financial companies: "
        f"{financial_df['company_id'].nunique()}"
    )

    print("\nGenerating peer-group radar charts...")

    peer_count = create_peer_group_charts(
        peer_df,
        composite_df,
    )

    print(
        f"Peer-group charts generated: "
        f"{peer_count}"
    )

    print("\nGenerating standalone charts...")

    standalone_count = create_standalone_charts(
        peer_df,
        financial_df,
        composite_df,
    )

    print(
        f"Standalone charts generated: "
        f"{standalone_count}"
    )

    total = peer_count + standalone_count

    print("\n" + "=" * 70)
    print("DAY 19 RADAR CHART SUMMARY")
    print("=" * 70)
    print(f"Peer-group charts: {peer_count}")
    print(f"Standalone charts: {standalone_count}")
    print(f"Total PNG charts: {total}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()