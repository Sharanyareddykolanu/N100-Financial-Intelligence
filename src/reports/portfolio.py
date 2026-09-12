from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"
PORTFOLIO_DIR = REPORTS_DIR / "portfolio"

P_AND_L = DATA_DIR / "profitandloss.xlsx"
BALANCE_SHEET = DATA_DIR / "balancesheet.xlsx"
RATIOS = DATA_DIR / "1788501620089-fb3ae469-financial_ratios.xlsx"

VALUATION_SUMMARY = OUTPUT_DIR / "valuation_summary.xlsx"

PORTFOLIO_PDF = PORTFOLIO_DIR / "portfolio_summary.pdf"


# ============================================================
# PAGE / COLORS
# ============================================================

PAGE_W, PAGE_H = A4

MARGIN = 12 * mm

NAVY = colors.HexColor("#102A43")
BLUE = colors.HexColor("#486581")
LIGHT_BLUE = colors.HexColor("#EAF1F8")
GREEN = colors.HexColor("#1B7F4B")
RED = colors.HexColor("#B42318")
GREY = colors.HexColor("#6B7280")
LIGHT_GREY = colors.HexColor("#F3F5F7")
BORDER = colors.HexColor("#D9E0E7")
DARK = colors.HexColor("#1F2933")
WHITE = colors.white


# ============================================================
# DATA HELPERS
# ============================================================

def read_excel(path: Path, header=0) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    return pd.read_excel(
        path,
        header=header,
    )


def clean_id(value) -> str:
    return str(value).strip()


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


def extract_year(value):

    match = re.search(
        r"(19|20)\d{2}",
        str(value),
    )

    if match:
        return int(match.group(0))

    return None


def add_year(df: pd.DataFrame) -> pd.DataFrame:

    out = df.copy()

    if "year" not in out.columns:
        return pd.DataFrame()

    out["_year"] = out["year"].map(
        extract_year
    )

    return out.dropna(
        subset=["_year"]
    )


def company_rows(
    df: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:

    if df.empty or "company_id" not in df.columns:
        return pd.DataFrame()

    return df[
        df["company_id"]
        .astype(str)
        .str.strip()
        .eq(clean_id(company_id))
    ].copy()


def fmt_cr(value) -> str:

    value = to_num(value)

    if math.isnan(value):
        return "N/A"

    return f"{value:,.0f} Cr"


def fmt_pct(value) -> str:

    value = to_num(value)

    if math.isnan(value):
        return "N/A"

    return f"{value:.1f}%"


def fmt_de(value) -> str:

    value = to_num(value)

    if math.isnan(value):
        return "N/A"

    return f"{value:.2f}"


# ============================================================
# ROCE
#
# ROCE = EBIT / (Equity + Reserves + Borrowings) * 100
# ============================================================

def calculate_roce_for_company(
    pnl: pd.DataFrame,
    bs: pd.DataFrame,
) -> pd.DataFrame:

    if pnl.empty or bs.empty:

        return pd.DataFrame(
            columns=[
                "year",
                "roce",
            ]
        )

    p = add_year(pnl)
    b = add_year(bs)

    if p.empty or b.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "roce",
            ]
        )

    required_pnl = [
        "operating_profit"
    ]

    required_bs = [
        "equity_capital",
        "reserves",
        "borrowings",
    ]

    if any(
        col not in p.columns
        for col in required_pnl
    ):
        return pd.DataFrame(
            columns=[
                "year",
                "roce",
            ]
        )

    if any(
        col not in b.columns
        for col in required_bs
    ):
        return pd.DataFrame(
            columns=[
                "year",
                "roce",
            ]
        )

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
        return pd.DataFrame(
            columns=[
                "year",
                "roce",
            ]
        )

    ebit = pd.to_numeric(
        merged["operating_profit"],
        errors="coerce",
    )

    capital = (
        pd.to_numeric(
            merged["equity_capital"],
            errors="coerce",
        )
        + pd.to_numeric(
            merged["reserves"],
            errors="coerce",
        )
        + pd.to_numeric(
            merged["borrowings"],
            errors="coerce",
        )
    )

    merged["roce"] = (
        ebit
        .div(
            capital.replace(
                0,
                math.nan,
            )
        )
        * 100
    )

    return merged[
        ["_year", "roce"]
    ].rename(
        columns={
            "_year": "year"
        }
    )


# ============================================================
# TREND ARROW
# ============================================================

def trend_arrow(
    latest,
    previous,
    higher_is_better=True,
) -> str:

    latest = to_num(latest)
    previous = to_num(previous)

    if (
        math.isnan(latest)
        or math.isnan(previous)
    ):
        return "→"

    if previous == 0:

        if latest == 0:
            return "→"

        if higher_is_better:
            return "↑" if latest > 0 else "↓"

        return "↓" if latest > 0 else "↑"

    change_pct = (
        (latest - previous)
        / abs(previous)
        * 100
    )

    if abs(change_pct) <= 2:
        return "→"

    if higher_is_better:
        return "↑" if change_pct > 0 else "↓"

    return "↓" if change_pct > 0 else "↑"


def arrow_color(
    arrow: str,
):

    if arrow == "↑":
        return GREEN

    if arrow == "↓":
        return RED

    return GREY


# ============================================================
# COMPANY UNIVERSE
# ============================================================

def load_company_universe():

    valuation = read_excel(
        VALUATION_SUMMARY,
        header=0,
    )

    required = [
        "company_id",
        "company_name",
        "ticker",
        "sector",
    ]

    missing = [
        col
        for col in required
        if col not in valuation.columns
    ]

    if missing:
        raise ValueError(
            f"valuation_summary.xlsx missing columns: {missing}"
        )

    valuation = valuation[
        required
    ].copy()

    valuation["company_id"] = (
        valuation["company_id"]
        .astype(str)
        .str.strip()
    )

    valuation["ticker"] = (
        valuation["ticker"]
        .astype(str)
        .str.strip()
    )

    valuation["company_name"] = (
        valuation["company_name"]
        .astype(str)
        .str.strip()
    )

    valuation["sector"] = (
        valuation["sector"]
        .fillna("N/A")
        .astype(str)
        .str.strip()
    )

    if len(valuation) != 92:
        raise ValueError(
            f"Expected 92 companies, found {len(valuation)}"
        )

    return valuation.sort_values(
        "ticker",
        key=lambda s: s.str.lower(),
    ).reset_index(drop=True)


# ============================================================
# DATA LOAD
# ============================================================

def load_data():

    pnl = read_excel(
        P_AND_L,
        header=1,
    )

    bs = read_excel(
        BALANCE_SHEET,
        header=1,
    )

    ratios = read_excel(
        RATIOS,
        header=0,
    )

    universe = load_company_universe()

    return {
        "pnl": pnl,
        "bs": bs,
        "ratios": ratios,
        "universe": universe,
    }


# ============================================================
# KPI EXTRACTION
# ============================================================

def extract_kpis(
    data,
    company_id: str,
):

    pnl = company_rows(
        data["pnl"],
        company_id,
    )

    bs = company_rows(
        data["bs"],
        company_id,
    )

    ratios = company_rows(
        data["ratios"],
        company_id,
    )

    pnl = add_year(pnl)
    bs = add_year(bs)
    ratios = add_year(ratios)

    if not pnl.empty:

        pnl = (
            pnl.sort_values("_year")
            .drop_duplicates(
                "_year",
                keep="last",
            )
        )

    if not bs.empty:

        bs = (
            bs.sort_values("_year")
            .drop_duplicates(
                "_year",
                keep="last",
            )
        )

    if not ratios.empty:

        ratios = (
            ratios.sort_values("_year")
            .drop_duplicates(
                "_year",
                keep="last",
            )
        )

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce = calculate_roce_for_company(
        pnl,
        bs,
    )

    roce_map = {}

    for _, row in roce.iterrows():

        roce_map[int(row["year"])] = to_num(
            row["roce"]
        )

    # --------------------------------------------------------
    # Build year map
    # --------------------------------------------------------

    all_years = set()

    for frame in [
        pnl,
        ratios,
        roce,
    ]:

        if frame is None or frame.empty:
            continue

        if "_year" in frame.columns:

            all_years.update(
                frame["_year"]
                .astype(int)
                .tolist()
            )

        elif "year" in frame.columns:

            all_years.update(
                frame["year"]
                .astype(int)
                .tolist()
            )

    years = sorted(
        all_years
    )

    if not years:
        return None

    latest_year = years[-1]

    previous_year = (
        years[-2]
        if len(years) >= 2
        else None
    )

    # --------------------------------------------------------
    # Latest / previous rows
    # --------------------------------------------------------

    latest_pnl = (
        pnl[pnl["_year"] == latest_year]
        if not pnl.empty
        else pd.DataFrame()
    )

    previous_pnl = (
        pnl[pnl["_year"] == previous_year]
        if previous_year is not None
        and not pnl.empty
        else pd.DataFrame()
    )

    latest_ratio = (
        ratios[
            ratios["_year"] == latest_year
        ]
        if not ratios.empty
        else pd.DataFrame()
    )

    previous_ratio = (
        ratios[
            ratios["_year"] == previous_year
        ]
        if previous_year is not None
        and not ratios.empty
        else pd.DataFrame()
    )

    lp = (
        latest_pnl.iloc[0]
        if not latest_pnl.empty
        else None
    )

    pp = (
        previous_pnl.iloc[0]
        if not previous_pnl.empty
        else None
    )

    lr = (
        latest_ratio.iloc[0]
        if not latest_ratio.empty
        else None
    )

    pr = (
        previous_ratio.iloc[0]
        if not previous_ratio.empty
        else None
    )

    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    revenue_latest = (
        lp["sales"]
        if lp is not None
        and "sales" in lp.index
        else math.nan
    )

    revenue_previous = (
        pp["sales"]
        if pp is not None
        and "sales" in pp.index
        else math.nan
    )

    # --------------------------------------------------------
    # Net Profit
    # --------------------------------------------------------

    profit_latest = (
        lp["net_profit"]
        if lp is not None
        and "net_profit" in lp.index
        else math.nan
    )

    profit_previous = (
        pp["net_profit"]
        if pp is not None
        and "net_profit" in pp.index
        else math.nan
    )

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    roe_latest = (
        lr["return_on_equity_pct"]
        if lr is not None
        and "return_on_equity_pct" in lr.index
        else math.nan
    )

    roe_previous = (
        pr["return_on_equity_pct"]
        if pr is not None
        and "return_on_equity_pct" in pr.index
        else math.nan
    )

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce_latest = roce_map.get(
        latest_year,
        math.nan,
    )

    roce_previous = (
        roce_map.get(
            previous_year,
            math.nan,
        )
        if previous_year is not None
        else math.nan
    )

    # --------------------------------------------------------
    # Debt / Equity
    # --------------------------------------------------------

    de_latest = (
        lr["debt_to_equity"]
        if lr is not None
        and "debt_to_equity" in lr.index
        else math.nan
    )

    de_previous = (
        pr["debt_to_equity"]
        if pr is not None
        and "debt_to_equity" in pr.index
        else math.nan
    )

    # --------------------------------------------------------
    # Free Cash Flow
    # --------------------------------------------------------

    fcf_latest = (
        lr["free_cash_flow_cr"]
        if lr is not None
        and "free_cash_flow_cr" in lr.index
        else math.nan
    )

    fcf_previous = (
        pr["free_cash_flow_cr"]
        if pr is not None
        and "free_cash_flow_cr" in pr.index
        else math.nan
    )

    # --------------------------------------------------------
    # Return KPIs
    # --------------------------------------------------------

    return {
        "latest_year": latest_year,
        "previous_year": previous_year,

        "revenue": revenue_latest,
        "revenue_previous": revenue_previous,
        "revenue_arrow": trend_arrow(
            revenue_latest,
            revenue_previous,
            higher_is_better=True,
        ),

        "net_profit": profit_latest,
        "net_profit_previous": profit_previous,
        "net_profit_arrow": trend_arrow(
            profit_latest,
            profit_previous,
            higher_is_better=True,
        ),

        "roe": roe_latest,
        "roe_previous": roe_previous,
        "roe_arrow": trend_arrow(
            roe_latest,
            roe_previous,
            higher_is_better=True,
        ),

        "roce": roce_latest,
        "roce_previous": roce_previous,
        "roce_arrow": trend_arrow(
            roce_latest,
            roce_previous,
            higher_is_better=True,
        ),

        "de": de_latest,
        "de_previous": de_previous,

        # Lower D/E is considered an improvement.
        "de_arrow": trend_arrow(
            de_latest,
            de_previous,
            higher_is_better=False,
        ),

        "fcf": fcf_latest,
        "fcf_previous": fcf_previous,
        "fcf_arrow": trend_arrow(
            fcf_latest,
            fcf_previous,
            higher_is_better=True,
        ),
    }


# ============================================================
# PDF DOCUMENT
# ============================================================

class PortfolioDoc(
    BaseDocTemplate
):

    def __init__(
        self,
        filename,
    ):

        super().__init__(
            str(filename),
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=12 * mm,
            bottomMargin=10 * mm,
            title="Nifty100 Portfolio Summary",
            author="Nifty100 Financial Intelligence",
        )

        frame = Frame(
            MARGIN,
            10 * mm,
            PAGE_W - 2 * MARGIN,
            PAGE_H - 22 * mm,
            id="portfolio",
        )

        self.addPageTemplates(
            [
                PageTemplate(
                    id="portfolio_page",
                    frames=[frame],
                    onPage=self.draw_page,
                )
            ]
        )

    @staticmethod
    def draw_page(
        canv,
        doc,
    ):

        canv.saveState()

        canv.setFillColor(NAVY)

        canv.rect(
            0,
            PAGE_H - 9 * mm,
            PAGE_W,
            9 * mm,
            fill=1,
            stroke=0,
        )

        canv.setFillColor(WHITE)

        canv.setFont(
            "Helvetica-Bold",
            7.5,
        )

        canv.drawString(
            MARGIN,
            PAGE_H - 5.8 * mm,
            "Nifty100 Financial Intelligence | Portfolio Summary",
        )

        canv.setFillColor(GREY)

        canv.setFont(
            "Helvetica",
            6,
        )

        canv.drawRightString(
            PAGE_W - MARGIN,
            5.5 * mm,
            f"Page {doc.page}",
        )

        canv.restoreState()


# ============================================================
# ONE COMPANY PAGE
# ============================================================

def make_company_page(
    row,
    kpis,
):

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PortfolioCompany",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=NAVY,
        spaceAfter=1.5 * mm,
    )

    ticker_style = ParagraphStyle(
        "PortfolioTicker",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=BLUE,
        spaceAfter=1 * mm,
    )

    sector_style = ParagraphStyle(
        "PortfolioSector",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=GREY,
        spaceAfter=4 * mm,
    )

    kpi_label = ParagraphStyle(
        "KpiLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.3,
        leading=7,
        textColor=GREY,
        alignment=TA_CENTER,
    )

    kpi_value = ParagraphStyle(
        "KpiValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=12,
        textColor=NAVY,
        alignment=TA_CENTER,
    )

    arrow_style = ParagraphStyle(
        "Arrow",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=12,
        alignment=TA_CENTER,
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    company_name = str(
        row["company_name"]
    )

    ticker = str(
        row["ticker"]
    )

    sector = str(
        row["sector"]
    )

    story = []

    story.append(
        Paragraph(
            company_name,
            title_style,
        )
    )

    story.append(
        Paragraph(
            ticker,
            ticker_style,
        )
    )

    story.append(
        Paragraph(
            f"Sector: {sector} | "
            f"Latest year: {kpis['latest_year']} | "
            f"Trend comparison: latest vs previous year",
            sector_style,
        )
    )

    # --------------------------------------------------------
    # KPI definitions
    # --------------------------------------------------------

    metrics = [
        (
            "Revenue",
            fmt_cr(
                kpis["revenue"]
            ),
            kpis["revenue_arrow"],
        ),
        (
            "Net Profit",
            fmt_cr(
                kpis["net_profit"]
            ),
            kpis["net_profit_arrow"],
        ),
        (
            "ROE",
            fmt_pct(
                kpis["roe"]
            ),
            kpis["roe_arrow"],
        ),
        (
            "ROCE",
            fmt_pct(
                kpis["roce"]
            ),
            kpis["roce_arrow"],
        ),
        (
            "Debt / Equity",
            fmt_de(
                kpis["de"]
            ),
            kpis["de_arrow"],
        ),
        (
            "Free Cash Flow",
            fmt_cr(
                kpis["fcf"]
            ),
            kpis["fcf_arrow"],
        ),
    ]

    # --------------------------------------------------------
    # KPI cells
    # --------------------------------------------------------

    kpi_cells = []

    for label, value, arrow in metrics:

        color = arrow_color(
            arrow
        )

        cell = Table(
            [
                [
                    Paragraph(
                        label,
                        kpi_label,
                    )
                ],
                [
                    Paragraph(
                        value,
                        kpi_value,
                    )
                ],
                [
                    Paragraph(
                        f'<font color="{color.hexval()}">'
                        f"{arrow}"
                        "</font>",
                        arrow_style,
                    )
                ],
            ],
            colWidths=[
                48 * mm
            ],
            rowHeights=[
                7 * mm,
                9 * mm,
                7 * mm,
            ],
        )

        cell.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        WHITE,
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
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
                        1 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        1 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0.5 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0.5 * mm,
                    ),
                ]
            )
        )

        kpi_cells.append(
            cell
        )

    kpi_table = Table(
        [
            kpi_cells[0:3],
            kpi_cells[3:6],
        ],
        colWidths=[
            51 * mm,
            51 * mm,
            51 * mm,
        ],
        rowHeights=[
            24 * mm,
            24 * mm,
        ],
    )

    kpi_table.setStyle(
        TableStyle(
            [
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
                    1.5 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    1.5 * mm,
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
        kpi_table
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    # --------------------------------------------------------
    # Trend explanation
    # --------------------------------------------------------

    trend_style = ParagraphStyle(
        "TrendLegend",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=DARK,
        spaceAfter=3 * mm,
    )

    story.append(
        Paragraph(
            "<b>Trend arrows:</b> "
            "↑ improved | "
            "↓ declined | "
            "→ flat within 2%. "
            "For Debt / Equity, a lower value is treated as an improvement.",
            trend_style,
        )
    )

    # --------------------------------------------------------
    # Latest vs previous table
    # --------------------------------------------------------

    compare_header = ParagraphStyle(
        "CompareHeader",
        fontName="Helvetica-Bold",
        fontSize=6.3,
        leading=7,
        textColor=WHITE,
        alignment=TA_CENTER,
        wordWrap="CJK",
    )

    compare_cell = ParagraphStyle(
        "CompareCell",
        fontName="Helvetica",
        fontSize=6.3,
        leading=7,
        textColor=DARK,
        alignment=TA_CENTER,
        wordWrap="CJK",
    )

    compare_left = ParagraphStyle(
        "CompareLeft",
        parent=compare_cell,
        alignment=TA_LEFT,
    )

    previous = kpis[
        "previous_year"
    ]

    comparison_rows = [
        [
            Paragraph(
                "KPI",
                compare_header,
            ),
            Paragraph(
                str(previous)
                if previous is not None
                else "Previous",
                compare_header,
            ),
            Paragraph(
                str(kpis["latest_year"]),
                compare_header,
            ),
            Paragraph(
                "Trend",
                compare_header,
            ),
        ]
    ]

    comparison_values = [
        (
            "Revenue",
            kpis["revenue_previous"],
            kpis["revenue"],
            kpis["revenue_arrow"],
        ),
        (
            "Net Profit",
            kpis["net_profit_previous"],
            kpis["net_profit"],
            kpis["net_profit_arrow"],
        ),
        (
            "ROE",
            kpis["roe_previous"],
            kpis["roe"],
            kpis["roe_arrow"],
        ),
        (
            "ROCE",
            kpis["roce_previous"],
            kpis["roce"],
            kpis["roce_arrow"],
        ),
        (
            "Debt / Equity",
            kpis["de_previous"],
            kpis["de"],
            kpis["de_arrow"],
        ),
        (
            "Free Cash Flow",
            kpis["fcf_previous"],
            kpis["fcf"],
            kpis["fcf_arrow"],
        ),
    ]

    for (
        name,
        previous_value,
        latest_value,
        arrow,
    ) in comparison_values:

        if name in {
            "Revenue",
            "Net Profit",
            "Free Cash Flow",
        }:

            previous_text = fmt_cr(
                previous_value
            )

            latest_text = fmt_cr(
                latest_value
            )

        elif name in {
            "ROE",
            "ROCE",
        }:

            previous_text = fmt_pct(
                previous_value
            )

            latest_text = fmt_pct(
                latest_value
            )

        else:

            previous_text = fmt_de(
                previous_value
            )

            latest_text = fmt_de(
                latest_value
            )

        comparison_rows.append(
            [
                Paragraph(
                    name,
                    compare_left,
                ),
                Paragraph(
                    previous_text,
                    compare_cell,
                ),
                Paragraph(
                    latest_text,
                    compare_cell,
                ),
                Paragraph(
                    arrow,
                    compare_cell,
                ),
            ]
        )

    comparison_table = Table(
        comparison_rows,
        colWidths=[
            43 * mm,
            45 * mm,
            45 * mm,
            25 * mm,
        ],
        repeatRows=1,
    )

    comparison_table.setStyle(
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
                    2 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2 * mm,
                ),
            ]
        )
    )

    story.append(
        comparison_table
    )

    return story


# ============================================================
# GENERATE PORTFOLIO PDF
# ============================================================

def generate_portfolio_pdf(
    data,
):

    universe = data[
        "universe"
    ]

    PORTFOLIO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    story = []

    successful = 0
    skipped = []

    for index, (_, row) in enumerate(
        universe.iterrows(),
        start=1,
    ):

        company_id = clean_id(
            row["company_id"]
        )

        try:

            kpis = extract_kpis(
                data,
                company_id,
            )

            if kpis is None:

                skipped.append(
                    {
                        "company_id": company_id,
                        "ticker": row["ticker"],
                        "reason": "No usable KPI data",
                    }
                )

                print(
                    f"[{index:02d}/92] "
                    f"SKIPPED {row['ticker']} "
                    f"-> No usable KPI data"
                )

                continue

            # ------------------------------------------------
            # IMPORTANT:
            # Add PageBreak BEFORE every successful company
            # except the first successful company.
            #
            # This avoids a blank page when the last company
            # or an earlier company is skipped.
            # ------------------------------------------------

            if successful > 0:
                story.append(
                    PageBreak()
                )

            story.extend(
                make_company_page(
                    row,
                    kpis,
                )
            )

            successful += 1

            print(
                f"[{index:02d}/92] "
                f"GENERATED {row['ticker']}"
            )

        except Exception as exc:

            skipped.append(
                {
                    "company_id": company_id,
                    "ticker": row["ticker"],
                    "reason": str(exc),
                }
            )

            print(
                f"[{index:02d}/92] "
                f"SKIPPED {row['ticker']} "
                f"-> {exc}"
            )

    # --------------------------------------------------------
    # Build PDF
    # --------------------------------------------------------

    doc = PortfolioDoc(
        PORTFOLIO_PDF
    )

    doc.build(
        story
    )

    # --------------------------------------------------------
    # Count pages
    # --------------------------------------------------------

    page_count = len(
        PdfReader(
            str(PORTFOLIO_PDF)
        ).pages
    )

    print("\n" + "=" * 60)
    print("PORTFOLIO PDF SUMMARY")
    print("=" * 60)

    print(
        f"Target companies : {len(universe)}"
    )

    print(
        f"Pages generated  : {page_count}"
    )

    print(
        f"Companies output : {successful}"
    )

    print(
        f"Companies skipped: {len(skipped)}"
    )

    print(
        f"PDF path         : {PORTFOLIO_PDF}"
    )

    # --------------------------------------------------------
    # Skipped log
    # --------------------------------------------------------

    if skipped:

        skipped_df = pd.DataFrame(
            skipped
        )

        skipped_path = (
            OUTPUT_DIR
            / "skipped_portfolio_pages.csv"
        )

        skipped_df.to_csv(
            skipped_path,
            index=False,
        )

        print(
            f"Skipped log      : {skipped_path}"
        )

    else:

        skipped_path = (
            OUTPUT_DIR
            / "skipped_portfolio_pages.csv"
        )

        # Remove old skipped log if everything succeeds.
        if skipped_path.exists():
            skipped_path.unlink()

    return (
        successful,
        skipped,
        page_count,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_portfolio_pdf(
    target_count,
    skipped,
    page_count,
):

    expected_pages = (
        target_count
        - len(skipped)
    )

    print("\n" + "=" * 60)
    print("DAY 35 PORTFOLIO VALIDATION")
    print("=" * 60)

    print(
        f"Expected pages: {expected_pages}"
    )

    print(
        f"Actual pages  : {page_count}"
    )

    if page_count != expected_pages:

        raise RuntimeError(
            "Portfolio page count mismatch: "
            f"expected {expected_pages}, "
            f"found {page_count}"
        )

    reader = PdfReader(
        str(PORTFOLIO_PDF)
    )

    blank_pages = 0

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        text = page.extract_text() or ""

        if not text.strip():

            blank_pages += 1

        if len(text.strip()) < 30:

            raise RuntimeError(
                f"Page {page_number} "
                "contains insufficient text."
            )

    print(
        f"Blank pages   : {blank_pages}"
    )

    if blank_pages:

        raise RuntimeError(
            f"Found {blank_pages} blank pages."
        )

    print(
        "Page validation: PASSED"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("DAY 35 - PORTFOLIO SUMMARY PDF")
    print("=" * 60)

    data = load_data()

    print(
        f"Loaded P&L rows   : {len(data['pnl'])}"
    )

    print(
        f"Loaded BS rows    : {len(data['bs'])}"
    )

    print(
        f"Loaded ratio rows : {len(data['ratios'])}"
    )

    print(
        f"Target companies  : {len(data['universe'])}"
    )

    successful, skipped, pages = (
        generate_portfolio_pdf(
            data
        )
    )

    validate_portfolio_pdf(
        len(data["universe"]),
        skipped,
        pages,
    )

    print("\n" + "=" * 60)
    print(
        "DAY 35 PORTFOLIO TEST STATUS: PASSED"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()