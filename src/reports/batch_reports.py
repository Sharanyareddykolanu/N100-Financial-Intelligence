from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"

TEARSHEET_DIR = REPORTS_DIR / "tearsheets"
SECTOR_DIR = REPORTS_DIR / "sector"

VALUATION_SUMMARY = OUTPUT_DIR / "valuation_summary.xlsx"
SKIPPED_OUTPUT = OUTPUT_DIR / "skipped_tearsheets.csv"

SECTOR_FILE = (
    DATA_DIR
    / "1788501621129-8684701e-sectors.xlsx"
)

TEARSHEET_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SECTOR_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# PAGE CONSTANTS
# ============================================================

PAGE_W, PAGE_H = A4


# ============================================================
# COLORS
# ============================================================

NAVY = colors.HexColor("#102A43")
BLUE = colors.HexColor("#486581")
GREY = colors.HexColor("#6B7280")
LIGHT_GREY = colors.HexColor("#F3F5F7")
DARK = colors.HexColor("#1F2933")
WHITE = colors.white
BORDER = colors.HexColor("#D9E0E7")


# ============================================================
# IMPORT DAY 33 TEARSHEET
# ============================================================

sys.path.insert(
    0,
    str(BASE_DIR / "src" / "reports"),
)

from tearsheet import (  # noqa: E402
    build_payload,
    build_tearsheet,
    load_data,
    read_excel_with_detected_header,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_id(value) -> str:
    return str(value).strip()


def safe_filename(value: str) -> str:

    text = clean_id(value)

    text = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        text,
    )

    text = re.sub(
        r"\s+",
        "_",
        text,
    )

    return text[:100] or "Unknown"


def to_num(
    value,
    default=math.nan,
) -> float:

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):

        return default


def fmt_num(
    value,
    decimals=1,
) -> str:

    value = to_num(value)

    if math.isnan(value):
        return "N/A"

    return f"{value:,.{decimals}f}"


def fmt(
    value,
    decimals=1,
) -> str:

    return fmt_num(
        value,
        decimals,
    )


def fmt_cr(value) -> str:
    return fmt_num(value, 0)


def fmt_pct(value) -> str:

    value = to_num(value)

    if math.isnan(value):
        return "N/A"

    return f"{value:.1f}%"


def extract_year(value):

    match = re.search(
        r"(19|20)\d{2}",
        str(value),
    )

    if match:
        return int(match.group(0))

    return None


def add_year_column(
    df: pd.DataFrame,
) -> pd.DataFrame:

    out = df.copy()

    if "year" not in out.columns:

        out["_year"] = math.nan

        return out

    out["_year"] = out["year"].map(
        extract_year
    )

    return out


# ============================================================
# AUTHORITATIVE 92-COMPANY UNIVERSE
# ============================================================

def load_target_companies() -> list[str]:

    if not VALUATION_SUMMARY.exists():
        raise FileNotFoundError(
            f"Missing: {VALUATION_SUMMARY}"
        )

    df = pd.read_excel(
        VALUATION_SUMMARY
    )

    if "company_id" not in df.columns:
        raise ValueError(
            "valuation_summary.xlsx does not contain company_id"
        )

    companies = (
        df["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .tolist()
    )

    if len(companies) != 92:
        raise ValueError(
            f"Expected 92 companies, found {len(companies)}"
        )

    return companies


# ============================================================
# COMPANY YEAR COVERAGE
# ============================================================

def company_year_count(
    data: dict,
    company_id: str,
) -> int:

    years = set()

    for key in [
        "pnl",
        "bs",
        "cf",
        "ratios",
    ]:

        frame = data.get(key)

        if (
            frame is None
            or "company_id" not in frame.columns
        ):
            continue

        rows = frame[
            frame["company_id"]
            .astype(str)
            .str.strip()
            .eq(clean_id(company_id))
        ]

        if rows.empty:
            continue

        rows = add_year_column(rows)

        valid = (
            rows["_year"]
            .dropna()
            .astype(int)
            .tolist()
        )

        years.update(valid)

    return len(years)


def latest_company_year(
    data: dict,
    company_id: str,
):

    years = set()

    for key in [
        "pnl",
        "bs",
        "cf",
        "ratios",
    ]:

        frame = data.get(key)

        if (
            frame is None
            or "company_id" not in frame.columns
        ):
            continue

        rows = frame[
            frame["company_id"]
            .astype(str)
            .str.strip()
            .eq(clean_id(company_id))
        ]

        if rows.empty:
            continue

        rows = add_year_column(rows)

        valid = (
            rows["_year"]
            .dropna()
            .astype(int)
            .tolist()
        )

        years.update(valid)

    return max(years) if years else None


# ============================================================
# REMOVE OLD BATCH OUTPUTS
# ============================================================

def clean_old_tearsheets():

    removed = 0

    for path in TEARSHEET_DIR.glob(
        "*_tearsheet.pdf"
    ):

        try:
            path.unlink()
            removed += 1
        except OSError:
            pass

    print(
        f"Old batch tearsheets removed: {removed}"
    )


def clean_old_sector_reports():

    removed = 0

    for path in SECTOR_DIR.glob(
        "*_report.pdf"
    ):

        try:
            path.unlink()
            removed += 1
        except OSError:
            pass

    print(
        f"Old sector reports removed: {removed}"
    )


# ============================================================
# BATCH TEARSHEETS
# ============================================================

def generate_batch_tearsheets(
    data: dict,
    target_companies: list[str],
):

    generated = []
    skipped = []

    print("\n" + "=" * 60)
    print("DAY 34 - BATCH TEARSHEET GENERATION")
    print("=" * 60)

    print(
        f"Target companies: {len(target_companies)}"
    )

    for index, company_id in enumerate(
        target_companies,
        start=1,
    ):

        company_id = clean_id(
            company_id
        )

        years = company_year_count(
            data,
            company_id,
        )

        if years < 3:

            skipped.append(
                {
                    "company_id": company_id,
                    "years_available": years,
                    "latest_year": latest_company_year(
                        data,
                        company_id,
                    ),
                    "reason": (
                        "Fewer than 3 years of data"
                    ),
                }
            )

            print(
                f"[{index:02d}/92] SKIPPED "
                f"{company_id} "
                f"({years} years)"
            )

            continue

        output_path = (
            TEARSHEET_DIR
            / f"{safe_filename(company_id)}_tearsheet.pdf"
        )

        build_tearsheet(
            company_id,
            output_path,
            data,
        )

        pages = len(
            PdfReader(
                str(output_path)
            ).pages
        )

        if pages != 2:

            raise RuntimeError(
                f"{company_id}: expected 2 pages, "
                f"found {pages}"
            )

        generated.append(
            {
                "company_id": company_id,
                "path": str(output_path),
                "pages": pages,
                "years_available": years,
            }
        )

        print(
            f"[{index:02d}/92] GENERATED "
            f"{company_id} "
            f"({years} years)"
        )

    skipped_df = pd.DataFrame(
        skipped,
        columns=[
            "company_id",
            "years_available",
            "latest_year",
            "reason",
        ],
    )

    skipped_df.to_csv(
        SKIPPED_OUTPUT,
        index=False,
    )

    print("\nBATCH SUMMARY")

    print(
        f"Generated tearsheets : {len(generated)}"
    )

    print(
        f"Skipped tearsheets   : {len(skipped)}"
    )

    print(
        f"Skipped log          : {SKIPPED_OUTPUT}"
    )

    return generated, skipped


# ============================================================
# BROAD SECTOR MAP
# ============================================================

def load_broad_sector_map(
    target_companies: list[str],
) -> dict[str, str]:

    if not SECTOR_FILE.exists():

        raise FileNotFoundError(
            f"Missing sector file: {SECTOR_FILE}"
        )

    sector_df = pd.read_excel(
        SECTOR_FILE,
        header=0,
    )

    required_columns = [
        "company_id",
        "broad_sector",
    ]

    missing = [
        col
        for col in required_columns
        if col not in sector_df.columns
    ]

    if missing:

        raise ValueError(
            f"Sector file missing columns: {missing}"
        )

    target_set = set(
        target_companies
    )

    sector_map = {}

    for _, row in sector_df.iterrows():

        company_id = clean_id(
            row["company_id"]
        )

        if company_id not in target_set:
            continue

        sector = row[
            "broad_sector"
        ]

        if pd.isna(sector):
            continue

        sector = str(
            sector
        ).strip()

        if sector:

            sector_map[
                company_id
            ] = sector

    return sector_map


def create_sector_groups(
    target_companies: list[str],
    sector_map: dict[str, str],
):

    groups = {}

    missing_sector = []

    for company_id in target_companies:

        sector = sector_map.get(
            company_id
        )

        if not sector:

            missing_sector.append(
                company_id
            )

            continue

        groups.setdefault(
            sector,
            [],
        ).append(company_id)

    if missing_sector:

        groups[
            "Unclassified"
        ] = missing_sector

    return {
        sector: sorted(companies)
        for sector, companies in groups.items()
    }


# ============================================================
# ROCE
# ============================================================

def latest_roce(
    data: dict,
    company_id: str,
):

    pnl = data["pnl"]
    bs = data["bs"]

    p = pnl[
        pnl["company_id"]
        .astype(str)
        .str.strip()
        .eq(clean_id(company_id))
    ].copy()

    b = bs[
        bs["company_id"]
        .astype(str)
        .str.strip()
        .eq(clean_id(company_id))
    ].copy()

    if p.empty or b.empty:
        return math.nan

    p = add_year_column(p)
    b = add_year_column(b)

    p = p.dropna(
        subset=["_year"]
    )

    b = b.dropna(
        subset=["_year"]
    )

    if p.empty or b.empty:
        return math.nan

    p["_year"] = p["_year"].astype(int)
    b["_year"] = b["_year"].astype(int)

    p = (
        p.sort_values("_year")
        .drop_duplicates(
            "_year",
            keep="last",
        )
    )

    b = (
        b.sort_values("_year")
        .drop_duplicates(
            "_year",
            keep="last",
        )
    )

    merged = p[
        [
            "_year",
            "operating_profit",
        ]
    ].merge(
        b[
            [
                "_year",
                "equity_capital",
                "reserves",
                "borrowings",
            ]
        ],
        on="_year",
        how="inner",
    )

    if merged.empty:
        return math.nan

    row = (
        merged
        .sort_values("_year")
        .iloc[-1]
    )

    ebit = to_num(
        row["operating_profit"]
    )

    capital_employed = (
        to_num(
            row["equity_capital"],
            0,
        )
        + to_num(
            row["reserves"],
            0,
        )
        + to_num(
            row["borrowings"],
            0,
        )
    )

    if (
        math.isnan(ebit)
        or capital_employed == 0
    ):
        return math.nan

    return (
        ebit
        / capital_employed
        * 100
    )


# ============================================================
# SECTOR METRICS
# ============================================================

def get_sector_metrics(
    data: dict,
    company_ids: list[str],
) -> pd.DataFrame:

    records = []

    cashflow_intel = data[
        "cashflow_intel"
    ]

    for company_id in company_ids:

        payload = build_payload(
            data,
            company_id,
        )

        intel = cashflow_intel[
            cashflow_intel["company_id"]
            .astype(str)
            .str.strip()
            .eq(clean_id(company_id))
        ]

        if intel.empty:

            cfo_quality = math.nan
            cfo_label = "N/A"

        else:

            intel_row = intel.iloc[0]

            cfo_quality = to_num(
                intel_row.get(
                    "cfo_quality_score"
                )
            )

            label = intel_row.get(
                "cfo_quality_label"
            )

            cfo_label = (
                "N/A"
                if pd.isna(label)
                else str(label)
            )

        records.append(
            {
                "company_id": company_id,
                "revenue": payload[
                    "latest_sales"
                ],
                "net_profit": payload[
                    "latest_profit"
                ],
                "roe": payload[
                    "latest_roe"
                ],
                "roce": latest_roce(
                    data,
                    company_id,
                ),
                "de": payload[
                    "latest_de"
                ],
                "fcf": payload[
                    "latest_fcf"
                ],
                "cfo_quality": cfo_quality,
                "cfo_quality_label": cfo_label,
                "capital_allocation": payload[
                    "capital_pattern"
                ],
            }
        )

    return pd.DataFrame(
        records
    )


# ============================================================
# WORD-WRAPPED PARAGRAPH
# ============================================================

def make_paragraph(
    value,
    style,
):

    text = (
        ""
        if value is None
        else str(value)
    )

    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return Paragraph(
        text,
        style,
    )


# ============================================================
# SECTOR PDF DOCUMENT
# ============================================================

class SectorDoc(
    BaseDocTemplate
):

    def __init__(
        self,
        filename,
        sector_name,
    ):

        super().__init__(
            str(filename),
            pagesize=A4,
            leftMargin=8 * mm,
            rightMargin=8 * mm,
            topMargin=16 * mm,
            bottomMargin=11 * mm,
            title=(
                f"{sector_name} "
                "Sector Report"
            ),
            author=(
                "Nifty100 "
                "Financial Intelligence"
            ),
        )

        frame = Frame(
            8 * mm,
            11 * mm,
            PAGE_W - 16 * mm,
            PAGE_H - 27 * mm,
            id="sector_frame",
        )

        self.sector_name = sector_name

        self.addPageTemplates(
            [
                PageTemplate(
                    id="sector",
                    frames=[frame],
                    onPage=self._header,
                )
            ]
        )

    def _header(
        self,
        canv,
        doc,
    ):

        canv.saveState()

        canv.setFillColor(NAVY)

        canv.rect(
            0,
            PAGE_H - 11 * mm,
            PAGE_W,
            11 * mm,
            fill=1,
            stroke=0,
        )

        canv.setFillColor(WHITE)

        canv.setFont(
            "Helvetica-Bold",
            8,
        )

        canv.drawString(
            8 * mm,
            PAGE_H - 7.2 * mm,
            (
                f"{self.sector_name} | "
                "Nifty100 Sector Report"
            ),
        )

        canv.setFillColor(GREY)

        canv.setFont(
            "Helvetica",
            6,
        )

        canv.drawRightString(
            PAGE_W - 8 * mm,
            5.5 * mm,
            f"Page {doc.page}",
        )

        canv.restoreState()


# ============================================================
# SECTOR PDF BUILDER
# ============================================================

def build_sector_pdf(
    sector_name: str,
    company_ids: list[str],
    data: dict,
):

    output_path = (
        SECTOR_DIR
        / f"{safe_filename(sector_name)}_report.pdf"
    )

    metrics = get_sector_metrics(
        data,
        company_ids,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SectorTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=15,
        textColor=NAVY,
        spaceAfter=3 * mm,
        wordWrap="CJK",
    )

    subtitle_style = ParagraphStyle(
        "SectorSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8,
        textColor=GREY,
        spaceAfter=3 * mm,
        wordWrap="CJK",
    )

    header_style = ParagraphStyle(
        "SectorHeader",
        fontName="Helvetica-Bold",
        fontSize=5.2,
        leading=6,
        textColor=WHITE,
        alignment=TA_CENTER,
        wordWrap="CJK",
    )

    cell_style = ParagraphStyle(
        "SectorCell",
        fontName="Helvetica",
        fontSize=4.8,
        leading=5.8,
        textColor=DARK,
        alignment=TA_CENTER,
        wordWrap="CJK",
    )

    cell_left = ParagraphStyle(
        "SectorCellLeft",
        parent=cell_style,
        alignment=TA_LEFT,
    )

    doc = SectorDoc(
        output_path,
        sector_name,
    )

    story = []

    # ========================================================
    # SUMMARY
    # ========================================================

    story.append(
        Paragraph(
            f"{sector_name} — Sector Summary",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"{len(company_ids)} companies | "
            "Median values from latest available data",
            subtitle_style,
        )
    )

    median_columns = [
        "revenue",
        "net_profit",
        "roe",
        "roce",
        "de",
        "fcf",
        "cfo_quality",
    ]

    medians = metrics[
        median_columns
    ].median(
        numeric_only=True
    )

    summary_rows = [
        [
            make_paragraph(
                "KPI",
                header_style,
            ),
            make_paragraph(
                "Sector Median",
                header_style,
            ),
        ],
        [
            make_paragraph(
                "Revenue (Cr)",
                cell_left,
            ),
            make_paragraph(
                fmt_cr(
                    medians["revenue"]
                ),
                cell_style,
            ),
        ],
        [
            make_paragraph(
                "Net Profit (Cr)",
                cell_left,
            ),
            make_paragraph(
                fmt_cr(
                    medians["net_profit"]
                ),
                cell_style,
            ),
        ],
        [
            make_paragraph(
                "ROE",
                cell_left,
            ),
            make_paragraph(
                fmt_pct(
                    medians["roe"]
                ),
                cell_style,
            ),
        ],
        [
            make_paragraph(
                "ROCE",
                cell_left,
            ),
            make_paragraph(
                fmt_pct(
                    medians["roce"]
                ),
                cell_style,
            ),
        ],
        [
            make_paragraph(
                "Debt / Equity",
                cell_left,
            ),
            make_paragraph(
                fmt(
                    medians["de"],
                    2,
                ),
                cell_style,
            ),
        ],
        [
            make_paragraph(
                "Free Cash Flow (Cr)",
                cell_left,
            ),
            make_paragraph(
                fmt_cr(
                    medians["fcf"]
                ),
                cell_style,
            ),
        ],
        [
            make_paragraph(
                "CFO Quality Score",
                cell_left,
            ),
            make_paragraph(
                fmt(
                    medians["cfo_quality"],
                    2,
                ),
                cell_style,
            ),
        ],
    ]

    summary_table = Table(
        summary_rows,
        colWidths=[
            58 * mm,
            35 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1.5 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1.5 * mm,
                ),
            ]
        )
    )

    story.append(
        summary_table
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    story.append(
        Paragraph(
            "All Companies — 8 Metrics",
            title_style,
        )
    )

    headers = [
        "Company",
        "Revenue",
        "Net Profit",
        "ROE",
        "ROCE",
        "D/E",
        "FCF",
        "CFO Quality",
        "Capital Allocation",
    ]

    table_rows = [
        [
            make_paragraph(
                header,
                header_style,
            )
            for header in headers
        ]
    ]

    for _, row in metrics.iterrows():

        table_rows.append(
            [
                make_paragraph(
                    row["company_id"],
                    cell_left,
                ),
                make_paragraph(
                    fmt_cr(
                        row["revenue"]
                    ),
                    cell_style,
                ),
                make_paragraph(
                    fmt_cr(
                        row["net_profit"]
                    ),
                    cell_style,
                ),
                make_paragraph(
                    fmt_pct(
                        row["roe"]
                    ),
                    cell_style,
                ),
                make_paragraph(
                    fmt_pct(
                        row["roce"]
                    ),
                    cell_style,
                ),
                make_paragraph(
                    fmt(
                        row["de"],
                        2,
                    ),
                    cell_style,
                ),
                make_paragraph(
                    fmt_cr(
                        row["fcf"]
                    ),
                    cell_style,
                ),
                make_paragraph(
                    row[
                        "cfo_quality_label"
                    ],
                    cell_style,
                ),
                make_paragraph(
                    row[
                        "capital_allocation"
                    ],
                    cell_style,
                ),
            ]
        )

    # Total width is approximately A4 width minus margins.
    col_widths = [
        23 * mm,
        17 * mm,
        19 * mm,
        10 * mm,
        10 * mm,
        10 * mm,
        16 * mm,
        21 * mm,
        31 * mm,
    ]

    company_table = Table(
        table_rows,
        colWidths=col_widths,
        repeatRows=1,
    )

    company_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    NAVY,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0.8 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0.8 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1.0 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1.0 * mm,
                ),
            ]
        )
    )

    story.append(
        company_table
    )

    doc.build(
        story
    )

    page_count = len(
        PdfReader(
            str(output_path)
        ).pages
    )

    return output_path, page_count


# ============================================================
# SECTOR REPORTS
# ============================================================

def generate_sector_reports(
    data: dict,
    target_companies: list[str],
):

    sector_map = load_broad_sector_map(
        target_companies
    )

    groups = create_sector_groups(
        target_companies,
        sector_map,
    )

    print("\n" + "=" * 60)
    print("DAY 34 - SECTOR REPORT GENERATION")
    print("=" * 60)

    print(
        f"Populated broad sectors: "
        f"{len(groups)}"
    )

    print("\nSector groups:")

    for sector_name in sorted(
        groups
    ):

        print(
            f"  {sector_name}: "
            f"{len(groups[sector_name])} companies"
        )

    generated = []

    for sector_name in sorted(
        groups
    ):

        company_ids = groups[
            sector_name
        ]

        path, pages = build_sector_pdf(
            sector_name,
            company_ids,
            data,
        )

        generated.append(
            {
                "sector": sector_name,
                "companies": len(
                    company_ids
                ),
                "pages": pages,
                "path": str(path),
            }
        )

        print(
            f"{sector_name:30s} | "
            f"{len(company_ids):2d} companies | "
            f"{pages} page(s)"
        )

    return generated


# ============================================================
# TEARSHEET SPOT CHECK
# ============================================================

def spot_check_tearsheets():

    companies = [
        "TCS",
        "HDFCBANK",
        "RELIANCE",
        "SUNPHARMA",
        "TATASTEEL",
    ]

    print("\n" + "=" * 60)
    print("DAY 34 SPOT CHECK")
    print("=" * 60)

    for company_id in companies:

        path = (
            TEARSHEET_DIR
            / f"{safe_filename(company_id)}_tearsheet.pdf"
        )

        if not path.exists():

            raise RuntimeError(
                f"Missing spot-check PDF: {path}"
            )

        reader = PdfReader(
            str(path)
        )

        pages = len(
            reader.pages
        )

        if pages != 2:

            raise RuntimeError(
                f"{company_id}: expected 2 pages, "
                f"found {pages}"
            )

        blank_pages = 0

        for page in reader.pages:

            text = page.extract_text() or ""

            if not text.strip():
                blank_pages += 1

        if blank_pages:

            raise RuntimeError(
                f"{company_id}: "
                f"{blank_pages} blank page(s)"
            )

        print(
            f"{company_id:10s} -> "
            "2 pages | "
            "blank pages: 0 | "
            "PDF QA: PASS"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("DAY 34 - BATCH REPORT GENERATION")
    print("=" * 60)

    data = load_data()

    target_companies = (
        load_target_companies()
    )

    print(
        f"Loaded authoritative universe: "
        f"{len(target_companies)} companies"
    )

    clean_old_tearsheets()
    clean_old_sector_reports()

    generated, skipped = (
        generate_batch_tearsheets(
            data,
            target_companies,
        )
    )

    sector_reports = (
        generate_sector_reports(
            data,
            target_companies,
        )
    )

    spot_check_tearsheets()

    actual_tearsheets = len(
        list(
            TEARSHEET_DIR.glob(
                "*_tearsheet.pdf"
            )
        )
    )

    expected_tearsheets = (
        len(target_companies)
        - len(skipped)
    )

    actual_sector_pdfs = len(
        list(
            SECTOR_DIR.glob(
                "*_report.pdf"
            )
        )
    )

    print("\n" + "=" * 60)
    print("DAY 34 FINAL VALIDATION")
    print("=" * 60)

    print(
        f"Target companies       : "
        f"{len(target_companies)}"
    )

    print(
        f"Generated tearsheets   : "
        f"{len(generated)}"
    )

    print(
        f"Skipped companies      : "
        f"{len(skipped)}"
    )

    print(
        f"Expected PDF count     : "
        f"{expected_tearsheets}"
    )

    print(
        f"Actual PDF count       : "
        f"{actual_tearsheets}"
    )

    print(
        f"Sector PDFs generated  : "
        f"{len(sector_reports)}"
    )

    print(
        f"Sector PDFs on disk    : "
        f"{actual_sector_pdfs}"
    )

    print(
        f"Skipped log            : "
        f"{SKIPPED_OUTPUT}"
    )

    if actual_tearsheets != expected_tearsheets:

        raise RuntimeError(
            "Tearsheet count mismatch: "
            f"expected {expected_tearsheets}, "
            f"found {actual_tearsheets}"
        )

    expected_sector_count = len(
        set(
            load_broad_sector_map(
                target_companies
            ).values()
        )
    )

    if actual_sector_pdfs != expected_sector_count:

        raise RuntimeError(
            "Sector PDF count mismatch: "
            f"expected {expected_sector_count}, "
            f"found {actual_sector_pdfs}"
        )

    print(
        "\nDay 34 test status: PASSED"
    )


if __name__ == "__main__":
    main()