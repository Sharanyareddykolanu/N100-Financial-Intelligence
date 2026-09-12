"""
DAY 36 - KMEANS CLUSTERING
Nifty100 Financial Intelligence

Requirements:
1. Five clustering features:
   - return_on_equity_pct
   - debt_to_equity
   - revenue_cagr_5yr
   - fcf_cagr_5yr
   - operating_profit_margin_pct

2. Sector-median imputation before scaling
3. StandardScaler
4. KMeans: 5 clusters, random_state=42
5. Elbow plot: K=2 to 10
6. Output:
   output/cluster_labels.csv
7. Validation
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "nifty100.db"

REPORTS_DIR = BASE_DIR / "reports"
OUTPUT_DIR = BASE_DIR / "output"

ELBOW_PATH = REPORTS_DIR / "elbow_plot.png"
CLUSTER_OUTPUT_PATH = OUTPUT_DIR / "cluster_labels.csv"


# ============================================================
# REQUIRED FEATURES
# ============================================================

FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


# ============================================================
# LOAD FINANCIAL RATIOS
# ============================================================

def load_ratio_data(conn):

    query = """
        SELECT
            company_id,
            year,
            return_on_equity_pct,
            debt_to_equity,
            revenue_cagr_5yr,
            operating_profit_margin_pct
        FROM financial_ratios
        ORDER BY company_id, year
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        raise ValueError(
            "financial_ratios table is empty."
        )

    return df


# ============================================================
# LOAD SECTOR DATA
# ============================================================

def load_sector_data(conn):

    query = """
        SELECT
            company_id,
            sector
        FROM company_sector
    """

    df = pd.read_sql_query(query, conn)

    if df.empty:
        raise ValueError(
            "company_sector table is empty."
        )

    return df


# ============================================================
# SELECT LATEST RATIO ROW
# ============================================================

def select_latest_ratios(df):

    df = df.copy()

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["company_id", "year"]
    )

    latest = (
        df.sort_values(
            ["company_id", "year"]
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="last"
        )
        .reset_index(drop=True)
    )

    return latest


# ============================================================
# CALCULATE FCF CAGR
# ============================================================

def calculate_fcf_cagr(conn):

    """
    The database free_cash_flow column is completely NULL.

    Therefore derive FCF as:

        FCF = Operating Cash Flow + Investing Cash Flow

    5-year CAGR:

        ((Ending FCF / Beginning FCF) ** (1/5) - 1) * 100

    CAGR is calculated only when both beginning
    and ending FCF are positive.
    """

    query = """
        SELECT
            company_id,
            year,
            operating_cash_flow,
            investing_cash_flow
        FROM company_cashflow
        ORDER BY company_id, year
    """

    cashflow = pd.read_sql_query(
        query,
        conn
    )

    if cashflow.empty:
        raise ValueError(
            "company_cashflow table is empty."
        )

    # Numeric conversion
    cashflow["year"] = pd.to_numeric(
        cashflow["year"],
        errors="coerce"
    )

    cashflow["operating_cash_flow"] = pd.to_numeric(
        cashflow["operating_cash_flow"],
        errors="coerce"
    )

    cashflow["investing_cash_flow"] = pd.to_numeric(
        cashflow["investing_cash_flow"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # DERIVE FCF
    # --------------------------------------------------------

    cashflow["derived_fcf"] = (
        cashflow["operating_cash_flow"]
        + cashflow["investing_cash_flow"]
    )

    results = []

    for company_id, group in cashflow.groupby(
        "company_id"
    ):

        group = (
            group
            .dropna(subset=["year"])
            .sort_values("year")
            .drop_duplicates(
                subset=["year"],
                keep="last"
            )
        )

        if group.empty:
            continue

        latest_year = int(
            group["year"].max()
        )

        old_year = latest_year - 5

        latest_data = group[
            group["year"] == latest_year
        ]

        old_data = group[
            group["year"] == old_year
        ]

        fcf_cagr = np.nan

        if (
            not latest_data.empty
            and not old_data.empty
        ):

            latest_fcf = latest_data.iloc[0][
                "derived_fcf"
            ]

            old_fcf = old_data.iloc[0][
                "derived_fcf"
            ]

            # Both values must be positive
            # for a mathematically valid CAGR.
            if (
                pd.notna(latest_fcf)
                and pd.notna(old_fcf)
                and latest_fcf > 0
                and old_fcf > 0
            ):

                fcf_cagr = (
                    (
                        latest_fcf /
                        old_fcf
                    ) ** (1 / 5)
                    - 1
                ) * 100

        results.append(
            {
                "company_id": company_id,
                "fcf_cagr_5yr": fcf_cagr
            }
        )

    return pd.DataFrame(results)


# ============================================================
# SECTOR-MEDIAN IMPUTATION
# ============================================================

def impute_sector_median(df):

    df = df.copy()

    for feature in FEATURES:

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce"
        )

        # Sector median
        sector_median = (
            df.groupby("sector")[feature]
            .transform("median")
        )

        df[feature] = df[feature].fillna(
            sector_median
        )

        # Overall median fallback
        overall_median = df[feature].median()

        df[feature] = df[feature].fillna(
            overall_median
        )

    return df


# ============================================================
# ELBOW PLOT
# ============================================================

def generate_elbow_plot(X_scaled):

    k_values = range(2, 11)

    inertias = []

    for k in k_values:

        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        model.fit(X_scaled)

        inertias.append(
            model.inertia_
        )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        list(k_values),
        inertias,
        marker="o"
    )

    plt.xlabel(
        "Number of Clusters (K)"
    )

    plt.ylabel(
        "Inertia"
    )

    plt.title(
        "K-Means Elbow Plot"
    )

    plt.xticks(
        list(k_values)
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        ELBOW_PATH,
        dpi=150
    )

    plt.close()

    return inertias


# ============================================================
# CLUSTER NAMES
# ============================================================

def assign_cluster_names(
    df,
    cluster_centers
):

    names = {}

    # Higher ROE + growth + OPM
    # and lower D/E generally indicate stronger quality.

    scores = []

    for cluster_id in range(5):

        center = cluster_centers[
            cluster_id
        ]

        roe = center[0]
        de = center[1]
        revenue_growth = center[2]
        fcf_growth = center[3]
        opm = center[4]

        score = (
            roe
            + revenue_growth
            + fcf_growth
            + opm
            - de
        )

        scores.append(
            (
                cluster_id,
                score
            )
        )

    scores.sort(
        key=lambda x: x[1],
        reverse=True
    )

    labels = [
        "High Quality Growth",
        "Strong Growth",
        "Balanced",
        "Moderate Quality",
        "Low Quality / High Risk",
    ]

    for index, (cluster_id, _) in enumerate(
        scores
    ):

        names[cluster_id] = labels[index]

    return names


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("DAY 36 - KMEANS CLUSTERING")
    print("=" * 60)

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        # ----------------------------------------------------
        # LOAD DATA
        # ----------------------------------------------------

        ratios = load_ratio_data(
            conn
        )

        sectors = load_sector_data(
            conn
        )

        fcf_cagr = calculate_fcf_cagr(
            conn
        )

    finally:

        conn.close()

    print(
        f"Financial ratio rows : {len(ratios)}"
    )

    # --------------------------------------------------------
    # LATEST COMPANY DATA
    # --------------------------------------------------------

    latest = select_latest_ratios(
        ratios
    )

    print(
        f"Latest company rows  : {len(latest)}"
    )

    print(
        f"Sector rows          : {len(sectors)}"
    )

    print(
        f"FCF CAGR rows        : {len(fcf_cagr)}"
    )

    # --------------------------------------------------------
    # MERGE FCF
    # --------------------------------------------------------

    data = latest.merge(
        fcf_cagr,
        on="company_id",
        how="left"
    )

    # --------------------------------------------------------
    # MERGE SECTOR
    # --------------------------------------------------------

    data = data.merge(
        sectors,
        on="company_id",
        how="left"
    )

    # Missing sector label
    data["sector"] = data["sector"].fillna(
        "Unknown"
    )

    # --------------------------------------------------------
    # BEFORE IMPUTATION
    # --------------------------------------------------------

    print()
    print(
        "Missing values BEFORE "
        "sector-median imputation:"
    )

    print(
        data[FEATURES].isna().sum()
    )

    # --------------------------------------------------------
    # IMPUTATION
    # --------------------------------------------------------

    data = impute_sector_median(
        data
    )

    # --------------------------------------------------------
    # AFTER IMPUTATION
    # --------------------------------------------------------

    print()
    print(
        "Missing values AFTER "
        "sector-median imputation:"
    )

    print(
        data[FEATURES].isna().sum()
    )

    # --------------------------------------------------------
    # FINAL MISSING VALUE CHECK
    # --------------------------------------------------------

    missing = data[
        FEATURES
    ].isna().sum()

    if missing.sum() > 0:

        print()
        print(
            "ERROR: Missing values remain:"
        )

        print(
            missing
        )

        raise ValueError(
            "Missing values remain after imputation."
        )

    print()
    print(
        "All clustering features are complete."
    )

    # --------------------------------------------------------
    # FEATURE MATRIX
    # --------------------------------------------------------

    X = data[
        FEATURES
    ].copy()

    # --------------------------------------------------------
    # STANDARD SCALER
    # --------------------------------------------------------

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        X
    )

    print(
        "StandardScaler         : PASSED"
    )

    # --------------------------------------------------------
    # ELBOW PLOT
    # --------------------------------------------------------

    inertias = generate_elbow_plot(
        X_scaled
    )

    print(
        f"Elbow plot saved       : {ELBOW_PATH}"
    )

    print(
        "K values tested        : 2 to 10"
    )

    print(
        "Selected K             : 5"
    )

    # --------------------------------------------------------
    # KMEANS
    # --------------------------------------------------------

    kmeans = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=10
    )

    cluster_ids = kmeans.fit_predict(
        X_scaled
    )

    data["cluster_id"] = cluster_ids

    # --------------------------------------------------------
    # DISTANCE FROM CENTROID
    # --------------------------------------------------------

    distances = kmeans.transform(
        X_scaled
    )

    data["distance_from_centroid"] = (
        distances[
            np.arange(
                len(data)
            ),
            cluster_ids
        ]
    )

    # --------------------------------------------------------
    # CLUSTER NAMES
    # --------------------------------------------------------

    # Convert centers back to original feature scale
    cluster_centers_original = (
        scaler.inverse_transform(
            kmeans.cluster_centers_
        )
    )

    cluster_names = assign_cluster_names(
        data,
        cluster_centers_original
    )

    data["cluster_name"] = (
        data["cluster_id"]
        .map(cluster_names)
    )

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    output = data[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    output = output.sort_values(
        [
            "cluster_id",
            "distance_from_centroid"
        ]
    )

    output.to_csv(
        CLUSTER_OUTPUT_PATH,
        index=False
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("DAY 36 VALIDATION")
    print("=" * 60)

    # Row count
    print(
        f"Companies clustered   : {len(output)}"
    )

    # Duplicate company check
    duplicate_count = (
        output["company_id"]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicate companies   : {duplicate_count}"
    )

    # Cluster IDs
    actual_clusters = sorted(
        output["cluster_id"]
        .unique()
        .tolist()
    )

    print(
        f"Cluster IDs           : {actual_clusters}"
    )

    # Distance check
    negative_distances = (
        output[
            "distance_from_centroid"
        ] < 0
    ).sum()

    print(
        f"Negative distances    : {negative_distances}"
    )

    # Null check
    null_output = (
        output.isna()
        .sum()
        .sum()
    )

    print(
        f"Output null values    : {null_output}"
    )

    # Cluster counts
    print()
    print(
        "Cluster distribution:"
    )

    print(
        output[
            "cluster_name"
        ].value_counts()
    )

    # --------------------------------------------------------
    # VALIDATION CONDITIONS
    # --------------------------------------------------------

    validation_passed = True

    if duplicate_count != 0:
        validation_passed = False

    if actual_clusters != [0, 1, 2, 3, 4]:
        validation_passed = False

    if negative_distances != 0:
        validation_passed = False

    if null_output != 0:
        validation_passed = False

    if len(output) == 0:
        validation_passed = False

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print()
    print(
        f"Output file           : "
        f"{CLUSTER_OUTPUT_PATH}"
    )

    print(
        f"Elbow plot            : "
        f"{ELBOW_PATH}"
    )

    print()

    if validation_passed:

        print(
            "DAY 36 TEST STATUS: PASSED"
        )

    else:

        print(
            "DAY 36 TEST STATUS: FAILED"
        )

        raise ValueError(
            "Day 36 validation failed."
        )

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()