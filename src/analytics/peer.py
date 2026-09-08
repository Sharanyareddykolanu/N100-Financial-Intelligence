"""
Day 18 - Peer Percentile Rankings

Requirements:
- Load peer_groups.xlsx
- Calculate PERCENT_RANK within each peer group and year
- Rank 10 financial metrics
- D/E is inverted so lower D/E = higher percentile
- Store results in SQLite table: peer_percentiles
- Companies without a peer group are reported but do not cause an error
"""

from pathlib import Path
import sqlite3

import pandas as pd


# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "nifty100.db"
PEER_FILE = PROJECT_ROOT / "peer_groups.xlsx"


# ---------------------------------------------------------------------
# METRIC CONFIGURATION
# ---------------------------------------------------------------------

METRICS = {
    "ROE": "return_on_equity_pct",
    "ROCE": "roce_pct",
    "Net Profit Margin": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "FCF": "free_cash_flow_cr",
    "PAT CAGR 5yr": "pat_cagr_5yr",
    "Revenue CAGR 5yr": "revenue_cagr_5yr",
    "EPS CAGR 5yr": "eps_cagr_5yr",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
}


# ---------------------------------------------------------------------
# LOAD PEER GROUPS
# ---------------------------------------------------------------------

def load_peer_groups():
    """Load peer group assignments from peer_groups.xlsx."""

    print("Loading peer_groups.xlsx...")

    if not PEER_FILE.exists():
        raise FileNotFoundError(
            f"Peer group file not found: {PEER_FILE}"
        )

    df = pd.read_excel(PEER_FILE)

    # Normalize column names
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    required_columns = {
        "id",
        "peer_group_name",
        "company_id",
        "is_benchmark",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns in peer_groups.xlsx: {sorted(missing)}"
        )

    # Clean values
    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["peer_group_name"] = (
        df["peer_group_name"]
        .astype(str)
        .str.strip()
    )

    print(f"Peer group rows: {len(df)}")
    print(f"Peer groups: {df['peer_group_name'].nunique()}")
    print(f"Companies assigned: {df['company_id'].nunique()}")

    return df


# ---------------------------------------------------------------------
# LOAD FINANCIAL DATA
# ---------------------------------------------------------------------

def load_financial_data():
    """
    Load financial data required for peer percentile calculations.

    ROCE is calculated from:
        Operating Profit / (Equity + Debt) * 100

    FCF comes from financial_ratios.free_cash_flow_cr because
    company_cashflow.free_cash_flow is unavailable in this database.
    """

    print()
    print("Loading financial data...")

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:
        query = """
        SELECT
            fr.company_id,
            fr.year,

            fr.return_on_equity_pct,
            fr.net_profit_margin_pct,
            fr.debt_to_equity,
            fr.free_cash_flow_cr,
            fr.pat_cagr_5yr,
            fr.revenue_cagr_5yr,
            fr.eps_cagr_5yr,
            fr.interest_coverage,
            fr.asset_turnover,

            cpl.operating_profit,
            cpl.net_profit,

            cbs.total_equity,
            cbs.debt

        FROM financial_ratios fr

        LEFT JOIN company_profit_loss cpl
            ON fr.company_id = cpl.company_id
            AND fr.year = cpl.year

        LEFT JOIN company_balance_sheet cbs
            ON fr.company_id = cbs.company_id
            AND fr.year = cbs.year
        """

        df = pd.read_sql_query(query, conn)

    finally:
        conn.close()

    # Normalize company IDs
    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Ensure year is numeric
    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce"
    ).astype("Int64")

    # Convert financial columns safely to numeric
    numeric_columns = [
        "return_on_equity_pct",
        "net_profit_margin_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "pat_cagr_5yr",
        "revenue_cagr_5yr",
        "eps_cagr_5yr",
        "interest_coverage",
        "asset_turnover",
        "operating_profit",
        "net_profit",
        "total_equity",
        "debt",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Calculate ROCE
    df["roce_pct"] = calculate_roce(df)

    print(f"Financial rows: {len(df)}")
    print(f"Financial companies: {df['company_id'].nunique()}")

    return df


# ---------------------------------------------------------------------
# ROCE
# ---------------------------------------------------------------------

def calculate_roce(df):
    """
    Calculate ROCE:

        ROCE = Operating Profit / (Equity + Debt) * 100

    Invalid or zero capital employed produces NaN.
    """

    operating_profit = pd.to_numeric(
        df["operating_profit"],
        errors="coerce"
    )

    equity = pd.to_numeric(
        df["total_equity"],
        errors="coerce"
    )

    debt = pd.to_numeric(
        df["debt"],
        errors="coerce"
    )

    capital_employed = equity + debt

    roce = (
        operating_profit
        / capital_employed
        * 100
    )

    roce = roce.where(
        capital_employed.notna()
        & (capital_employed != 0)
    )

    return roce


# ---------------------------------------------------------------------
# PERCENT RANK
# ---------------------------------------------------------------------

def calculate_percent_rank(group):
    """
    Calculate SQL-style PERCENT_RANK.

    Formula:

        (rank - 1) / (count - 1)

    Missing values:
    - are excluded from ranking
    - remain NaN

    Single valid observation:
    - percentile = 0.0

    This implementation deliberately converts pd.NA/object values
    into regular numeric values before constructing the result.
    """

    # Convert the incoming group to a normal pandas Series
    values = pd.Series(
        list(group),
        index=group.index,
        dtype="object",
    )

    # Safely convert to numeric
    numeric_values = pd.to_numeric(
        values,
        errors="coerce",
    )

    # Always create a regular float result
    result = pd.Series(
        float("nan"),
        index=group.index,
        dtype="float64",
    )

    # Identify valid numeric values
    valid = numeric_values.notna()

    # Nothing to rank
    if valid.sum() == 0:
        return result

    valid_values = numeric_values.loc[valid]

    count = len(valid_values)

    # One valid value
    if count == 1:
        result.loc[valid] = 0.0
        return result

    # SQL-style RANK()
    ranks = valid_values.rank(
        method="min",
        ascending=True,
    )

    # PERCENT_RANK
    percentile = (
        (ranks - 1)
        / (count - 1)
    )

    # Force normal float values
    percentile = percentile.astype(float)

    result.loc[valid] = percentile

    return result


# ---------------------------------------------------------------------
# BUILD PEER PERCENTILES
# ---------------------------------------------------------------------

def build_peer_percentiles(
    financial_data,
    peer_groups,
):
    """
    Merge financial data with peer groups and calculate percentile
    rankings for all 10 metrics.
    """

    print()
    print("Calculating peer percentiles...")

    # Keep only necessary peer-group columns
    peers = peer_groups[
        [
            "peer_group_name",
            "company_id",
            "is_benchmark",
        ]
    ].copy()

    # Remove accidental duplicate company assignments
    peers = peers.drop_duplicates(
        subset=["company_id"],
        keep="first",
    )

    # Merge
    merged = financial_data.merge(
        peers,
        on="company_id",
        how="left",
    )

    # Find companies without a peer group
    missing_companies = (
        merged.loc[
            merged["peer_group_name"].isna(),
            "company_id",
        ]
        .dropna()
        .unique()
    )

    for company_id in sorted(missing_companies):
        print(
            f"{company_id}: No peer group assigned"
        )

    # Only assigned companies participate in rankings
    assigned = merged[
        merged["peer_group_name"].notna()
    ].copy()

    if assigned.empty:
        raise ValueError(
            "No companies were matched to peer groups."
        )

    # Make sure year is a regular numeric type where possible
    assigned["year"] = pd.to_numeric(
        assigned["year"],
        errors="coerce",
    )

    results = []

    # ---------------------------------------------------------------
    # Calculate each metric
    # ---------------------------------------------------------------

    for metric_name, column_name in METRICS.items():

        print(
            f"  Calculating {metric_name}..."
        )

        if column_name not in assigned.columns:
            print(
                f"    WARNING: {column_name} not available"
            )
            continue

        working = assigned[
            [
                "company_id",
                "peer_group_name",
                "year",
                column_name,
            ]
        ].copy()

        # Convert values to numeric
        working["value"] = pd.to_numeric(
            working[column_name],
            errors="coerce",
        )

        # -----------------------------------------------------------
        # Percent rank within peer group AND year
        # -----------------------------------------------------------

        working["percentile_rank"] = (
            working
            .groupby(
                [
                    "peer_group_name",
                    "year",
                ],
                dropna=False,
                sort=False,
                group_keys=False,
            )["value"]
            .transform(calculate_percent_rank)
        )

        # -----------------------------------------------------------
        # D/E inversion
        #
        # Normal percentile:
        #     higher D/E = higher percentile
        #
        # Required:
        #     lower D/E = higher percentile
        #
        # Therefore:
        #     1 - percentile
        # -----------------------------------------------------------

        if metric_name == "D/E":

            valid = (
                working["percentile_rank"]
                .notna()
            )

            working.loc[
                valid,
                "percentile_rank",
            ] = (
                1
                - working.loc[
                    valid,
                    "percentile_rank",
                ]
            )

        # Keep required output columns
        output = working[
            [
                "company_id",
                "peer_group_name",
                "year",
                "value",
                "percentile_rank",
            ]
        ].copy()

        output["metric"] = metric_name

        results.append(output)

    if not results:
        raise ValueError(
            "No peer percentile metrics were calculated."
        )

    # Combine all metrics
    result = pd.concat(
        results,
        ignore_index=True,
    )

    # Arrange exact requested column order
    result = result[
        [
            "company_id",
            "peer_group_name",
            "metric",
            "value",
            "percentile_rank",
            "year",
        ]
    ]

    return result


# ---------------------------------------------------------------------
# CREATE SQLITE TABLE
# ---------------------------------------------------------------------

def create_peer_percentiles_table(conn):
    """Create or replace peer_percentiles table."""

    conn.execute(
        """
        DROP TABLE IF EXISTS peer_percentiles
        """
    )

    conn.execute(
        """
        CREATE TABLE peer_percentiles (
            company_id TEXT NOT NULL,
            peer_group_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            percentile_rank REAL,
            year INTEGER
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX idx_peer_percentiles_company
        ON peer_percentiles(company_id)
        """
    )

    conn.execute(
        """
        CREATE INDEX idx_peer_percentiles_group_metric_year
        ON peer_percentiles(
            peer_group_name,
            metric,
            year
        )
        """
    )

    conn.commit()


# ---------------------------------------------------------------------
# WRITE TO SQLITE
# ---------------------------------------------------------------------

def write_to_database(result):
    """Write peer percentile results to SQLite."""

    print()
    print("Writing peer_percentiles table...")

    conn = sqlite3.connect(DB_PATH)

    try:

        create_peer_percentiles_table(conn)

        # Replace pandas NA/NaN with None for SQLite
        clean = result.copy()

        clean = clean.astype(
            {
                "company_id": "object",
                "peer_group_name": "object",
                "metric": "object",
            }
        )

        clean = clean.where(
            pd.notna(clean),
            None,
        )

        rows = clean[
            [
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ]
        ].itertuples(
            index=False,
            name=None,
        )

        conn.executemany(
            """
            INSERT INTO peer_percentiles (
                company_id,
                peer_group_name,
                metric,
                value,
                percentile_rank,
                year
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        conn.commit()

    finally:
        conn.close()


# ---------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------

def validate_result(result):
    """Validate Day 18 output."""

    print()
    print("=" * 70)
    print("DAY 18 VALIDATION")
    print("=" * 70)

    print(
        f"Total percentile rows: {len(result)}"
    )

    print(
        f"Unique companies: "
        f"{result['company_id'].nunique()}"
    )

    print(
        f"Peer groups: "
        f"{result['peer_group_name'].nunique()}"
    )

    print(
        f"Metrics: "
        f"{result['metric'].nunique()}"
    )

    # Expected
    expected_metrics = set(METRICS.keys())
    actual_metrics = set(result["metric"].unique())

    print()
    print("Expected metrics:", len(expected_metrics))
    print("Actual metrics:", len(actual_metrics))

    missing_metrics = (
        expected_metrics - actual_metrics
    )

    if missing_metrics:
        print(
            "WARNING - Missing metrics:",
            sorted(missing_metrics),
        )
    else:
        print("All 10 metrics present: PASS")

    # Percentile range
    valid_percentiles = result[
        result["percentile_rank"].notna()
    ]["percentile_rank"]

    invalid_percentiles = valid_percentiles[
        (valid_percentiles < 0)
        | (valid_percentiles > 1)
    ]

    print()
    print(
        "Invalid percentile ranks:",
        len(invalid_percentiles),
    )

    if len(invalid_percentiles) == 0:
        print(
            "Percentile range 0-1: PASS"
        )
    else:
        print(
            "Percentile range 0-1: FAIL"
        )

    # Metric counts
    print()
    print("Rows by metric:")

    metric_counts = (
        result
        .groupby("metric")
        .size()
        .sort_index()
    )

    for metric, count in metric_counts.items():
        print(
            f"  {metric}: {count}"
        )

    # Peer-group counts
    print()
    print("Rows by peer group:")

    group_counts = (
        result
        .groupby("peer_group_name")
        .size()
        .sort_index()
    )

    for group_name, count in group_counts.items():
        print(
            f"  {group_name}: {count}"
        )

    # D/E check
    print()
    print("D/E inversion check:")

    de = result[
        result["metric"] == "D/E"
    ].copy()

    de_valid = de[
        de["value"].notna()
        & de["percentile_rank"].notna()
    ]

    if not de_valid.empty:

        # Lowest D/E should generally have highest percentile.
        lowest_de = de_valid.loc[
            de_valid["value"].idxmin()
        ]

        highest_de = de_valid.loc[
            de_valid["value"].idxmax()
        ]

        print(
            f"  Lowest D/E: "
            f"{lowest_de['company_id']} "
            f"= {lowest_de['value']:.4f}, "
            f"percentile "
            f"{lowest_de['percentile_rank']:.4f}"
        )

        print(
            f"  Highest D/E: "
            f"{highest_de['company_id']} "
            f"= {highest_de['value']:.4f}, "
            f"percentile "
            f"{highest_de['percentile_rank']:.4f}"
        )

    # Sample
    print()
    print("Sample rows:")

    print(
        result.head(10).to_string(
            index=False
        )
    )

    print()
    print("=" * 70)


# ---------------------------------------------------------------------
# DATABASE VALIDATION
# ---------------------------------------------------------------------

def validate_database():
    """Verify that the SQLite table was written correctly."""

    print()
    print("Checking SQLite database...")

    conn = sqlite3.connect(DB_PATH)

    try:

        row_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM peer_percentiles
            """
        ).fetchone()[0]

        company_count = conn.execute(
            """
            SELECT COUNT(DISTINCT company_id)
            FROM peer_percentiles
            """
        ).fetchone()[0]

        group_count = conn.execute(
            """
            SELECT COUNT(DISTINCT peer_group_name)
            FROM peer_percentiles
            """
        ).fetchone()[0]

        metric_count = conn.execute(
            """
            SELECT COUNT(DISTINCT metric)
            FROM peer_percentiles
            """
        ).fetchone()[0]

        invalid_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM peer_percentiles
            WHERE percentile_rank IS NOT NULL
              AND (
                  percentile_rank < 0
                  OR percentile_rank > 1
              )
            """
        ).fetchone()[0]

    finally:
        conn.close()

    print(
        f"SQLite rows: {row_count}"
    )

    print(
        f"SQLite companies: {company_count}"
    )

    print(
        f"SQLite peer groups: {group_count}"
    )

    print(
        f"SQLite metrics: {metric_count}"
    )

    print(
        f"Invalid SQLite percentiles: "
        f"{invalid_count}"
    )

    if invalid_count == 0:
        print(
            "SQLite percentile validation: PASS"
        )
    else:
        print(
            "SQLite percentile validation: FAIL"
        )


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():

    print("=" * 70)
    print("DAY 18 - PEER PERCENTILE RANKINGS")
    print("=" * 70)

    # Step 1
    peer_groups = load_peer_groups()

    # Step 2
    financial_data = load_financial_data()

    # Step 3
    result = build_peer_percentiles(
        financial_data,
        peer_groups,
    )

    # Step 4
    validate_result(result)

    # Step 5
    write_to_database(result)

    # Step 6
    validate_database()

    print()
    print("=" * 70)
    print("DAY 18 COMPLETED SUCCESSFULLY")
    print("=" * 70)

    print()
    print(
        "Output table: peer_percentiles"
    )

    print(
        f"Rows inserted: {len(result)}"
    )

    print(
        "Database:",
        DB_PATH,
    )


if __name__ == "__main__":
    main()