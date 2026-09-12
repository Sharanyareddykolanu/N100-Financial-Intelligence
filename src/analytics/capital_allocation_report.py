from pathlib import Path

import pandas as pd


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]

CAPITAL_ALLOCATION = BASE_DIR / "output" / "capital_allocation.csv"
VALUATION_SUMMARY = BASE_DIR / "output" / "valuation_summary.xlsx"
CASHFLOW_EXCEL = BASE_DIR / "output" / "cashflow_intelligence.xlsx"

DISTRIBUTION_OUTPUT = BASE_DIR / "output" / "capital_allocation_distribution.csv"
PATTERN_CHANGES_OUTPUT = BASE_DIR / "output" / "pattern_changes.csv"


# ------------------------------------------------------------
# Required columns
# ------------------------------------------------------------
REQUIRED_COLUMNS = [
    "company_id",
    "year",
    "cfo_sign",
    "cfi_sign",
    "cff_sign",
    "pattern_label",
]


# ------------------------------------------------------------
# Load authoritative 92-company universe
# ------------------------------------------------------------
def load_target_companies() -> set[str]:
    df = pd.read_excel(VALUATION_SUMMARY)

    if "company_id" not in df.columns:
        raise ValueError("valuation_summary.xlsx does not contain company_id")

    companies = (
        df["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    return set(companies)


# ------------------------------------------------------------
# Load capital allocation
# ------------------------------------------------------------
def load_capital_allocation() -> pd.DataFrame:
    df = pd.read_csv(CAPITAL_ALLOCATION)

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"capital_allocation.csv missing columns: {missing}"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
    )

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    return df


# ------------------------------------------------------------
# Filter to target universe
# ------------------------------------------------------------
def filter_target_universe(
    capital_df: pd.DataFrame,
    target_companies: set[str],
) -> pd.DataFrame:

    filtered = capital_df[
        capital_df["company_id"].isin(target_companies)
    ].copy()

    extra = sorted(
        set(capital_df["company_id"]) - target_companies
    )

    missing = sorted(
        target_companies - set(capital_df["company_id"])
    )

    print(f"Target companies             : {len(target_companies)}")
    print(f"Capital allocation companies : {capital_df['company_id'].nunique()}")
    print(f"Rows before filtering        : {len(capital_df)}")
    print(f"Rows after filtering         : {len(filtered)}")
    print(f"Unexpected companies removed : {len(extra)}")
    print(f"Target companies missing     : {len(missing)}")

    if extra:
        print(f"Removed companies: {extra}")

    if missing:
        print(f"Missing target companies: {missing}")

    return filtered


# ------------------------------------------------------------
# Coverage
# ------------------------------------------------------------
def print_coverage(
    capital_df: pd.DataFrame,
    target_companies: set[str],
) -> None:

    print("\nCOVERAGE CHECK")

    present = set(capital_df["company_id"])

    missing = sorted(
        target_companies - present
    )

    print(f"92-company universe           : {len(target_companies)}")
    print(f"Companies with capital data   : {len(present)}")
    print(f"Companies missing capital data: {len(missing)}")

    if missing:
        print(f"Missing companies             : {missing}")

    if not capital_df.empty:
        years = capital_df["year"].dropna().astype(int)

        print(
            f"Year range                    : "
            f"{years.min()} to {years.max()}"
        )

        counts = (
            capital_df
            .groupby("company_id")["year"]
            .nunique()
        )

        print(f"Min years/company              : {counts.min()}")
        print(f"Max years/company              : {counts.max()}")

    print(
        "Note: companies listed later naturally have fewer historical years."
    )


# ------------------------------------------------------------
# Latest year distribution
# ------------------------------------------------------------
def create_latest_distribution(
    capital_df: pd.DataFrame,
    target_companies: set[str],
) -> pd.DataFrame:

    if capital_df.empty:
        raise ValueError("No capital allocation data available.")

    latest_year = int(
        capital_df["year"].max()
    )

    latest = capital_df[
        capital_df["year"] == latest_year
    ].copy()

    counts = (
        latest.groupby("pattern_label")["company_id"]
        .nunique()
        .to_dict()
    )

    expected_patterns = [
        "Reinvestor",
        "Shareholder Returns",
        "Distress Signal",
        "Growth Funded by Debt",
        "Liquidating Assets",
        "Cash Accumulator",
        "Pre-Revenue",
        "Mixed",
        "Unknown",
    ]

    rows = []

    for pattern in expected_patterns:
        rows.append(
            {
                "year": latest_year,
                "pattern_label": pattern,
                "company_count": int(
                    counts.get(pattern, 0)
                ),
            }
        )

    represented = set(
        latest["company_id"]
    )

    missing_latest = (
        target_companies - represented
    )

    if missing_latest:
        rows.append(
            {
                "year": latest_year,
                "pattern_label": "N/A",
                "company_count": len(missing_latest),
            }
        )

    result = pd.DataFrame(rows)

    result.to_csv(
        DISTRIBUTION_OUTPUT,
        index=False,
    )

    print("\nLATEST-YEAR DISTRIBUTION")
    print(f"Latest year: {latest_year}")
    print(result.to_string(index=False))
    print(
        f"\nTotal represented: "
        f"{result['company_count'].sum()}"
    )
    print(
        f"Created: {DISTRIBUTION_OUTPUT}"
    )

    return result


# ------------------------------------------------------------
# Pattern changes
# ------------------------------------------------------------
def create_pattern_changes(
    capital_df: pd.DataFrame,
) -> pd.DataFrame:

    df = capital_df[
        [
            "company_id",
            "year",
            "pattern_label",
        ]
    ].copy()

    df = df.sort_values(
        ["company_id", "year"]
    )

    changes = []

    for company_id, group in df.groupby("company_id"):

        group = (
            group
            .sort_values("year")
            .reset_index(drop=True)
        )

        for i in range(1, len(group)):

            previous = group.iloc[i - 1]
            current = group.iloc[i]

            previous_year = int(
                previous["year"]
            )

            current_year = int(
                current["year"]
            )

            # Only compare consecutive calendar years.
            if current_year - previous_year != 1:
                continue

            previous_pattern = previous["pattern_label"]
            current_pattern = current["pattern_label"]

            if previous_pattern == current_pattern:
                continue

            changes.append(
                {
                    "company_id": company_id,
                    "previous_year": previous_year,
                    "previous_pattern": previous_pattern,
                    "latest_year": current_year,
                    "latest_pattern": current_pattern,
                    "change": (
                        f"{previous_pattern} -> "
                        f"{current_pattern}"
                    ),
                }
            )

    result = pd.DataFrame(
        changes,
        columns=[
            "company_id",
            "previous_year",
            "previous_pattern",
            "latest_year",
            "latest_pattern",
            "change",
        ],
    )

    result.to_csv(
        PATTERN_CHANGES_OUTPUT,
        index=False,
    )

    print("\nPATTERN CHANGES")
    print(f"Changes found: {len(result)}")

    if not result.empty:
        print(
            result.head(20).to_string(
                index=False
            )
        )

    print(
        f"\nCreated: {PATTERN_CHANGES_OUTPUT}"
    )

    return result


# ------------------------------------------------------------
# Update cash-flow Excel
# ------------------------------------------------------------
def update_cashflow_excel(
    target_companies: set[str],
    capital_df: pd.DataFrame,
) -> pd.DataFrame:

    if not CASHFLOW_EXCEL.exists():
        raise FileNotFoundError(
            f"Missing file: {CASHFLOW_EXCEL}"
        )

    cashflow = pd.read_excel(CASHFLOW_EXCEL)

    if "company_id" not in cashflow.columns:
        raise ValueError(
            "cashflow_intelligence.xlsx does not contain company_id"
        )

    cashflow["company_id"] = (
        cashflow["company_id"]
        .astype(str)
        .str.strip()
    )

    latest_year = int(capital_df["year"].max())

    latest_patterns = (
        capital_df[
            capital_df["year"] == latest_year
        ][
            ["company_id", "pattern_label"]
        ]
        .drop_duplicates(subset=["company_id"])
        .rename(
            columns={
                "pattern_label": "capital_allocation_pattern"
            }
        )
    )

    # Remove old copy before merging.
    cashflow = cashflow.drop(
        columns=["capital_allocation_pattern"],
        errors="ignore",
    )

    # Keep all companies from the Day 31 cash-flow workbook.
    updated = cashflow.merge(
        latest_patterns,
        on="company_id",
        how="left",
    )

    # Explicitly label companies without a capital-allocation pattern.
    updated["capital_allocation_pattern"] = (
        updated["capital_allocation_pattern"]
        .fillna("N/A")
    )

    updated = (
        updated
        .sort_values("company_id")
        .reset_index(drop=True)
    )

    with pd.ExcelWriter(
        CASHFLOW_EXCEL,
        engine="openpyxl",
        mode="w",
    ) as writer:
        updated.to_excel(
            writer,
            index=False,
            sheet_name="cashflow_intelligence",
        )

    print("\nCASH FLOW EXCEL UPDATE")
    print(f"Latest capital year : {latest_year}")
    print(f"Rows in updated file: {len(updated)}")
    print("Added column        : capital_allocation_pattern")
    print(
        "N/A capital pattern : "
        f"{(updated['capital_allocation_pattern'] == 'N/A').sum()}"
    )
    print(f"Updated: {CASHFLOW_EXCEL}")

    return updated