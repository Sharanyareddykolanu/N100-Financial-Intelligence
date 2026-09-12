from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
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
    Flowable,
)
from pypdf import PdfReader


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
TEST_DIR = OUTPUT_DIR / "tearsheet_tests"

P_AND_L = DATA_DIR / "profitandloss.xlsx"
BALANCE_SHEET = DATA_DIR / "balancesheet.xlsx"
CASH_FLOW = DATA_DIR / "cashflow.xlsx"
RATIOS = DATA_DIR / "1788501620089-fb3ae469-financial_ratios.xlsx"
COMPANIES = DATA_DIR / "companies.xlsx"

PROS_CONS = OUTPUT_DIR / "pros_cons_generated.csv"
CAPITAL_ALLOCATION = OUTPUT_DIR / "capital_allocation.csv"
CASHFLOW_INTELLIGENCE = OUTPUT_DIR / "cashflow_intelligence.xlsx"


# ============================================================
# PAGE / COLORS
# ============================================================

PAGE_W, PAGE_H = A4

MARGIN = 11 * mm
HEADER_H = 22 * mm
BOTTOM_MARGIN = 10 * mm

NAVY = colors.HexColor("#102A43")
BLUE = colors.HexColor("#486581")
LIGHT_BLUE = colors.HexColor("#EAF1F8")
GREEN = colors.HexColor("#1B7F4B")
LIGHT_GREEN = colors.HexColor("#EAF6EF")
RED = colors.HexColor("#B42318")
LIGHT_RED = colors.HexColor("#FDECEC")
GREY = colors.HexColor("#6B7280")
LIGHT_GREY = colors.HexColor("#F3F5F7")
BORDER = colors.HexColor("#D9E0E7")
DARK = colors.HexColor("#1F2933")
WHITE = colors.white


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_id(value) -> str:
    return str(value).strip()


def to_num(value, default=math.nan) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


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


def fmt_ratio(value) -> str:
    value = to_num(value)
    if math.isnan(value):
        return "N/A"
    return f"{value:.2f}"


def extract_year(value):
    if pd.isna(value):
        return None

    match = re.search(r"(19|20)\d{2}", str(value))

    if match:
        return int(match.group(0))

    return None


def add_year_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_year"] = out["year"].map(extract_year)
    out = out.dropna(subset=["_year"]).copy()
    out["_year"] = out["_year"].astype(int)
    return out


def company_rows(df: pd.DataFrame, company_id: str) -> pd.DataFrame:
    if "company_id" not in df.columns:
        return df.iloc[0:0].copy()

    mask = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .eq(clean_id(company_id))
    )

    return df.loc[mask].copy()


# ============================================================
# ROBUST EXCEL HEADER DETECTION
# ============================================================

def read_excel_with_detected_header(
    path: Path,
    required_column: str = "company_id",
) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    preview = pd.read_excel(
        path,
        header=None,
        nrows=8,
    )

    header_row = None

    for i in range(len(preview)):
        values = {
            str(x).strip().lower()
            for x in preview.iloc[i].tolist()
            if not pd.isna(x)
        }

        if required_column.lower() in values:
            header_row = i
            break

    if header_row is None:
        # Most raw project files have the actual header on row 2.
        header_row = 0 if required_column in preview.iloc[0].astype(str).tolist() else 1

    df = pd.read_excel(
        path,
        header=header_row,
    )

    df = df.dropna(axis=0, how="all")
    df = df.dropna(axis=1, how="all")

    return df


# ============================================================
# DATA LOADING
# ============================================================

def load_data():
    pnl = read_excel_with_detected_header(P_AND_L)
    bs = read_excel_with_detected_header(BALANCE_SHEET)
    cf = read_excel_with_detected_header(CASH_FLOW)
    ratios = read_excel_with_detected_header(RATIOS)

    pros_cons = pd.read_csv(PROS_CONS)
    capital = pd.read_csv(CAPITAL_ALLOCATION)

    cashflow_intel = read_excel_with_detected_header(
        CASHFLOW_INTELLIGENCE
    )

    companies = None

    if COMPANIES.exists():
        try:
            companies = read_excel_with_detected_header(
                COMPANIES
            )
        except Exception:
            companies = None

    return {
        "pnl": pnl,
        "bs": bs,
        "cf": cf,
        "ratios": ratios,
        "pros_cons": pros_cons,
        "capital": capital,
        "cashflow_intel": cashflow_intel,
        "companies": companies,
    }


# ============================================================
# COMPANY NAME / TICKER
# ============================================================

def get_company_identity(
    data,
    company_id: str,
):
    companies = data["companies"]

    if companies is not None and "company_id" in companies.columns:

        rows = company_rows(
            companies,
            company_id,
        )

        if not rows.empty:
            row = rows.iloc[0]

            possible_name_columns = [
                "company_name",
                "name",
                "company",
            ]

            possible_ticker_columns = [
                "ticker",
                "symbol",
            ]

            name = company_id

            for col in possible_name_columns:
                if col in companies.columns:
                    value = row[col]
                    if not pd.isna(value) and str(value).strip():
                        name = str(value).strip()
                        break

            ticker = company_id

            for col in possible_ticker_columns:
                if col in companies.columns:
                    value = row[col]
                    if not pd.isna(value) and str(value).strip():
                        ticker = str(value).strip()
                        break

            return name, ticker

    return company_id, company_id


# ============================================================
# ROCE
# Formula:
# ROCE = EBIT / (Equity + Reserves + Borrowings) * 100
# Existing project definition.
# ============================================================

def calculate_roce(
    pnl: pd.DataFrame,
    bs: pd.DataFrame,
) -> pd.DataFrame:

    if pnl.empty or bs.empty:
        return pd.DataFrame(
            columns=["year", "roce"]
        )

    p = add_year_column(pnl)
    b = add_year_column(bs)

    p = (
        p.sort_values(["_year", "id"])
        if "id" in p.columns
        else p.sort_values("_year")
    )

    b = (
        b.sort_values(["_year", "id"])
        if "id" in b.columns
        else b.sort_values("_year")
    )

    p = p.drop_duplicates(
        "_year",
        keep="last",
    )

    b = b.drop_duplicates(
        "_year",
        keep="last",
    )

    merged = p[
        ["_year", "operating_profit"]
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

    ebit = pd.to_numeric(
        merged["operating_profit"],
        errors="coerce",
    )

    capital_employed = (
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
        .div(capital_employed.replace(0, math.nan))
        .mul(100)
    )

    return merged[
        ["_year", "roce"]
    ].rename(
        columns={"_year": "year"}
    )


# ============================================================
# COMPANY PAYLOAD
# ============================================================

def build_payload(
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

    cf = company_rows(
        data["cf"],
        company_id,
    )

    ratios = company_rows(
        data["ratios"],
        company_id,
    )

    pros_cons = company_rows(
        data["pros_cons"],
        company_id,
    )

    capital = company_rows(
        data["capital"],
        company_id,
    )

    # --------------------------------------------------------
    # Year normalization
    # --------------------------------------------------------

    pnl = add_year_column(pnl)
    bs = add_year_column(bs)
    cf = add_year_column(cf)
    ratios = add_year_column(ratios)
    capital = add_year_column(capital)

    # --------------------------------------------------------
    # Latest ratio
    # --------------------------------------------------------

    latest_ratio = None

    if not ratios.empty:
        latest_ratio = (
            ratios.sort_values("_year")
            .drop_duplicates(
                "_year",
                keep="last",
            )
            .iloc[-1]
        )

    # --------------------------------------------------------
    # Latest P&L
    # --------------------------------------------------------

    latest_pnl = None

    if not pnl.empty:
        latest_pnl = (
            pnl.sort_values("_year")
            .drop_duplicates(
                "_year",
                keep="last",
            )
            .iloc[-1]
        )

    # --------------------------------------------------------
    # Latest cash flow
    # --------------------------------------------------------

    latest_cf = None

    if not cf.empty:
        latest_cf = (
            cf.sort_values("_year")
            .drop_duplicates(
                "_year",
                keep="last",
            )
            .iloc[-1]
        )

    # --------------------------------------------------------
    # Revenue / profit chart
    # --------------------------------------------------------

    chart_pnl = (
        pnl.sort_values("_year")
        .drop_duplicates("_year", keep="last")
        .tail(10)
    )

    revenue_years = chart_pnl["_year"].astype(int).tolist()

    revenue = (
        pd.to_numeric(
            chart_pnl["sales"],
            errors="coerce",
        )
        .fillna(0)
        .tolist()
    )

    net_profit = (
        pd.to_numeric(
            chart_pnl["net_profit"],
            errors="coerce",
        )
        .fillna(0)
        .tolist()
    )

    # --------------------------------------------------------
    # ROE
    # --------------------------------------------------------

    ratio_chart = (
        ratios.sort_values("_year")
        .drop_duplicates("_year", keep="last")
        .tail(10)
    )

    roe_map = {}

    for _, row in ratio_chart.iterrows():
        roe_map[int(row["_year"])] = to_num(
            row.get("return_on_equity_pct")
        )

    # --------------------------------------------------------
    # ROCE
    # --------------------------------------------------------

    roce_df = calculate_roce(
        pnl,
        bs,
    )

    roce_map = {}

    for _, row in roce_df.iterrows():
        roce_map[int(row["year"])] = to_num(
            row["roce"]
        )

    trend_years = sorted(
        set(roe_map).intersection(roce_map)
    )[-10:]

    roe_values = [
        roe_map[y] if not math.isnan(roe_map[y]) else 0
        for y in trend_years
    ]

    roce_values = [
        roce_map[y] if not math.isnan(roce_map[y]) else 0
        for y in trend_years
    ]

    # --------------------------------------------------------
    # Balance sheet
    # --------------------------------------------------------

    chart_bs = (
        bs.sort_values("_year")
        .drop_duplicates("_year", keep="last")
        .tail(10)
    )

    bs_years = chart_bs["_year"].astype(int).tolist()

    equity = (
        pd.to_numeric(
            chart_bs["equity_capital"],
            errors="coerce",
        )
        .fillna(0)
        .tolist()
    )

    borrowings = (
        pd.to_numeric(
            chart_bs["borrowings"],
            errors="coerce",
        )
        .fillna(0)
        .tolist()
    )

    other_liabilities = (
        pd.to_numeric(
            chart_bs["other_liabilities"],
            errors="coerce",
        )
        .fillna(0)
        .tolist()
    )

    # --------------------------------------------------------
    # Pros / Cons
    # --------------------------------------------------------

    pros = []
    cons = []

    if not pros_cons.empty:

        pros = (
            pros_cons[
                pros_cons["type"]
                .astype(str)
                .str.lower()
                .eq("pro")
            ]["text"]
            .dropna()
            .astype(str)
            .tolist()
        )

        cons = (
            pros_cons[
                pros_cons["type"]
                .astype(str)
                .str.lower()
                .eq("con")
            ]["text"]
            .dropna()
            .astype(str)
            .tolist()
        )

    # --------------------------------------------------------
    # Capital allocation
    # --------------------------------------------------------

    capital_pattern = "N/A"

    if not capital.empty:

        latest_capital = (
            capital.sort_values("_year")
            .drop_duplicates(
                "_year",
                keep="last",
            )
            .iloc[-1]
        )

        value = latest_capital.get(
            "pattern_label"
        )

        if not pd.isna(value):
            capital_pattern = str(value)

    # --------------------------------------------------------
    # Latest KPI values
    # --------------------------------------------------------

    latest_sales = (
        latest_pnl.get("sales")
        if latest_pnl is not None
        else math.nan
    )

    latest_profit = (
        latest_pnl.get("net_profit")
        if latest_pnl is not None
        else math.nan
    )

    latest_roe = (
        latest_ratio.get("return_on_equity_pct")
        if latest_ratio is not None
        else math.nan
    )

    latest_de = (
        latest_ratio.get("debt_to_equity")
        if latest_ratio is not None
        else math.nan
    )

    latest_fcf = (
        latest_ratio.get("free_cash_flow_cr")
        if latest_ratio is not None
        else math.nan
    )

    latest_roce = (
        roce_values[-1]
        if roce_values
        else math.nan
    )

    # --------------------------------------------------------
    # Latest cash flow
    # --------------------------------------------------------

    latest_cfo = (
        latest_cf.get("operating_activity")
        if latest_cf is not None
        else 0
    )

    latest_cfi = (
        latest_cf.get("investing_activity")
        if latest_cf is not None
        else 0
    )

    latest_cff = (
        latest_cf.get("financing_activity")
        if latest_cf is not None
        else 0
    )

    latest_net_cash = (
        latest_cf.get("net_cash_flow")
        if latest_cf is not None
        else (
            to_num(latest_cfo, 0)
            + to_num(latest_cfi, 0)
            + to_num(latest_cff, 0)
        )
    )

    return {
        "company_id": company_id,
        "revenue_years": revenue_years,
        "revenue": revenue,
        "net_profit": net_profit,
        "trend_years": trend_years,
        "roe": roe_values,
        "roce": roce_values,
        "bs_years": bs_years,
        "equity": equity,
        "borrowings": borrowings,
        "other_liabilities": other_liabilities,
        "pros": pros,
        "cons": cons,
        "capital_pattern": capital_pattern,
        "latest_sales": to_num(latest_sales),
        "latest_profit": to_num(latest_profit),
        "latest_roe": to_num(latest_roe),
        "latest_roce": to_num(latest_roce),
        "latest_de": to_num(latest_de),
        "latest_fcf": to_num(latest_fcf),
        "latest_cfo": to_num(latest_cfo, 0),
        "latest_cfi": to_num(latest_cfi, 0),
        "latest_cff": to_num(latest_cff, 0),
        "latest_net_cash": to_num(latest_net_cash, 0),
    }


# ============================================================
# PAGE HEADER
# ============================================================

def draw_header(
    canv,
    doc,
    company_name,
    ticker,
):

    canv.saveState()

    canv.setFillColor(NAVY)
    canv.rect(
        0,
        PAGE_H - HEADER_H,
        PAGE_W,
        HEADER_H,
        fill=1,
        stroke=0,
    )

    canv.setFillColor(WHITE)

    canv.setFont(
        "Helvetica-Bold",
        17,
    )

    canv.drawString(
        MARGIN,
        PAGE_H - 9 * mm,
        company_name[:60],
    )

    canv.setFont(
        "Helvetica",
        8.5,
    )

    canv.drawString(
        MARGIN,
        PAGE_H - 15.5 * mm,
        f"{ticker}",
    )

    canv.setFont(
        "Helvetica",
        6.5,
    )

    canv.drawRightString(
        PAGE_W - MARGIN,
        6 * mm,
        f"Nifty100 Financial Intelligence | Page {doc.page}",
    )

    canv.restoreState()


# ============================================================
# CUSTOM DRAWINGS
# ============================================================

class ChartBox(Flowable):
    def __init__(
        self,
        title,
        width,
        height,
        draw_function,
    ):
        super().__init__()
        self.title = title
        self.width = width
        self.height = height
        self.draw_function = draw_function

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):

        c = self.canv

        # Outer box.
        c.setStrokeColor(BORDER)
        c.setFillColor(WHITE)

        c.roundRect(
            0,
            0,
            self.width,
            self.height,
            2.5 * mm,
            stroke=1,
            fill=1,
        )

        # Title.
        c.setFillColor(NAVY)
        c.setFont(
            "Helvetica-Bold",
            8,
        )

        c.drawString(
            4 * mm,
            self.height - 6 * mm,
            self.title,
        )

        # Chart area.
        self.draw_function(
            c,
            10 * mm,
            6 * mm,
            self.width - 18 * mm,
            self.height - 16 * mm,
        )


# ============================================================
# REVENUE / NET PROFIT
# ============================================================

def draw_revenue_profit(
    values_revenue,
    values_profit,
    years,
):

    def drawer(c, x, y, w, h):

        if not years:
            c.setFillColor(GREY)
            c.setFont("Helvetica", 7)
            c.drawString(x, y + h / 2, "No financial trend data available.")
            return

        max_value = max(
            max(values_revenue or [0]),
            max(values_profit or [0]),
            1,
        )

        plot_h = h - 14
        plot_w = w - 5

        step = plot_w / len(years)

        bar_w = max(
            3,
            step * 0.28,
        )

        c.setStrokeColor(LIGHT_GREY)

        for i in range(1, 5):
            gy = y + plot_h * i / 5
            c.line(
                x,
                gy,
                x + plot_w,
                gy,
            )

        for i, year in enumerate(years):

            cx = x + step * (i + 0.5)

            rv = max(0, to_num(values_revenue[i], 0))
            np = max(0, to_num(values_profit[i], 0))

            rh = rv / max_value * plot_h
            ph = np / max_value * plot_h

            c.setFillColor(NAVY)
            c.rect(
                cx - bar_w - 1,
                y,
                bar_w,
                rh,
                fill=1,
                stroke=0,
            )

            c.setFillColor(BLUE)
            c.rect(
                cx + 1,
                y,
                bar_w,
                ph,
                fill=1,
                stroke=0,
            )

            if i == 0 or i == len(years) - 1 or i % 2 == 0:
                c.setFillColor(GREY)
                c.setFont("Helvetica", 5.5)
                c.drawCentredString(
                    cx,
                    y - 6,
                    str(year),
                )

        # Legend.
        c.setFillColor(NAVY)
        c.rect(
            x + plot_w - 78,
            y + plot_h + 3,
            6,
            6,
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)
        c.setFont("Helvetica", 5.8)
        c.drawString(
            x + plot_w - 68,
            y + plot_h + 3,
            "Revenue",
        )

        c.setFillColor(BLUE)
        c.rect(
            x + plot_w - 37,
            y + plot_h + 3,
            6,
            6,
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)
        c.drawString(
            x + plot_w - 27,
            y + plot_h + 3,
            "Net Profit",
        )

    return drawer


# ============================================================
# ROE / ROCE DUAL AXIS
# ============================================================

def draw_roe_roce(
    years,
    roe,
    roce,
):

    def drawer(c, x, y, w, h):

        if not years:
            c.setFillColor(GREY)
            c.setFont("Helvetica", 7)
            c.drawString(
                x,
                y + h / 2,
                "No ROE/ROCE trend data available.",
            )
            return

        plot_h = h - 14
        plot_w = w - 26

        max_left = max(
            [abs(to_num(v, 0)) for v in roe] + [10]
        )

        max_right = max(
            [abs(to_num(v, 0)) for v in roce] + [10]
        )

        def px(i):
            if len(years) == 1:
                return x + plot_w / 2
            return x + plot_w * i / (len(years) - 1)

        def py_left(value):
            return y + plot_h * (
                (value + max_left)
                / (2 * max_left)
            )

        def py_right(value):
            return y + plot_h * (
                (value + max_right)
                / (2 * max_right)
            )

        zero_left = py_left(0)

        c.setStrokeColor(LIGHT_GREY)
        c.line(
            x,
            zero_left,
            x + plot_w,
            zero_left,
        )

        # ROE line.
        c.setStrokeColor(NAVY)
        c.setLineWidth(1.6)

        for i in range(1, len(years)):
            x1 = px(i - 1)
            x2 = px(i)

            y1 = py_left(
                to_num(roe[i - 1], 0)
            )

            y2 = py_left(
                to_num(roe[i], 0)
            )

            c.line(
                x1,
                y1,
                x2,
                y2,
            )

        # ROCE line.
        c.setStrokeColor(GREEN)

        for i in range(1, len(years)):
            x1 = px(i - 1)
            x2 = px(i)

            y1 = py_right(
                to_num(roce[i - 1], 0)
            )

            y2 = py_right(
                to_num(roce[i], 0)
            )

            c.line(
                x1,
                y1,
                x2,
                y2,
            )

        # X labels.
        c.setFillColor(GREY)
        c.setFont("Helvetica", 5.5)

        for i, year in enumerate(years):

            if i == 0 or i == len(years) - 1 or i % 2 == 0:

                c.drawCentredString(
                    px(i),
                    y - 6,
                    str(year),
                )

        # Left/right labels.
        c.setFont(
            "Helvetica",
            5.5,
        )

        c.setFillColor(NAVY)

        c.drawString(
            x - 2,
            y + plot_h + 2,
            "ROE %",
        )

        c.setFillColor(GREEN)

        c.drawRightString(
            x + plot_w + 20,
            y + plot_h + 2,
            "ROCE %",
        )

        # Legend.
        c.setFillColor(NAVY)
        c.rect(
            x + plot_w - 48,
            y + plot_h + 2,
            5,
            5,
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)
        c.drawString(
            x + plot_w - 40,
            y + plot_h + 1,
            "ROE",
        )

        c.setFillColor(GREEN)
        c.rect(
            x + plot_w - 18,
            y + plot_h + 2,
            5,
            5,
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)
        c.drawString(
            x + plot_w - 10,
            y + plot_h + 1,
            "ROCE",
        )

    return drawer


# ============================================================
# BALANCE SHEET STACKED BAR
# ============================================================

def draw_balance_sheet(
    years,
    equity,
    borrowings,
    other_liabilities,
):

    def drawer(c, x, y, w, h):

        if not years:
            c.setFillColor(GREY)
            c.setFont("Helvetica", 7)
            c.drawString(
                x,
                y + h / 2,
                "No balance sheet data available.",
            )
            return

        plot_h = h - 14
        plot_w = w - 5

        totals = [
            max(0, to_num(equity[i], 0))
            + max(0, to_num(borrowings[i], 0))
            + max(0, to_num(other_liabilities[i], 0))
            for i in range(len(years))
        ]

        max_total = max(
            totals or [1]
        )

        step = plot_w / len(years)

        bar_w = max(
            5,
            step * 0.56,
        )

        for i, year in enumerate(years):

            cx = x + step * (i + 0.5)

            components = [
                (
                    equity[i],
                    NAVY,
                ),
                (
                    borrowings[i],
                    BLUE,
                ),
                (
                    other_liabilities[i],
                    colors.HexColor("#AAB7C4"),
                ),
            ]

            current_y = y

            for value, fill in components:

                value = max(
                    0,
                    to_num(value, 0),
                )

                bar_h = (
                    value
                    / max_total
                    * plot_h
                )

                c.setFillColor(fill)

                c.rect(
                    cx - bar_w / 2,
                    current_y,
                    bar_w,
                    bar_h,
                    fill=1,
                    stroke=0,
                )

                current_y += bar_h

            if (
                i == 0
                or i == len(years) - 1
                or i % 2 == 0
            ):
                c.setFillColor(GREY)
                c.setFont(
                    "Helvetica",
                    5.5,
                )

                c.drawCentredString(
                    cx,
                    y - 6,
                    str(year),
                )

        # Legend.
        legend = [
            (NAVY, "Equity"),
            (BLUE, "Borrowings"),
            (colors.HexColor("#AAB7C4"), "Other liabilities"),
        ]

        lx = x + 2

        for fill, label in legend:

            c.setFillColor(fill)
            c.rect(
                lx,
                y + plot_h + 3,
                6,
                6,
                fill=1,
                stroke=0,
            )

            c.setFillColor(DARK)
            c.setFont(
                "Helvetica",
                5.8,
            )

            c.drawString(
                lx + 9,
                y + plot_h + 3,
                label,
            )

            lx += 74

    return drawer


# ============================================================
# CASH FLOW WATERFALL
# ============================================================

def draw_waterfall(
    cfo,
    cfi,
    cff,
    net_cash,
):

    def drawer(c, x, y, w, h):

        values = [
            ("CFO", to_num(cfo, 0)),
            ("CFI", to_num(cfi, 0)),
            ("CFF", to_num(cff, 0)),
        ]

        # Calculate true running waterfall.
        running = 0
        starts = []
        ends = []

        for _, value in values:

            starts.append(running)

            running += value

            ends.append(running)

        # Net Cash Flow final bar.
        net_value = to_num(net_cash, 0)

        all_levels = [0]

        for value in starts + ends:
            all_levels.append(value)

        all_levels.append(net_value)

        min_level = min(all_levels)
        max_level = max(all_levels)

        spread = max(
            max_level - min_level,
            1,
        )

        plot_h = h - 20

        def py(value):
            return (
                y
                + (value - min_level)
                / spread
                * plot_h
            )

        zero_y = py(0)

        # Zero line.
        c.setStrokeColor(GREY)
        c.setLineWidth(0.7)
        c.line(
            x,
            zero_y,
            x + w,
            zero_y,
        )

        step = w / 4
        bar_w = min(
            30,
            step * 0.45,
        )

        for i, ((label, value), start, end) in enumerate(
            zip(values, starts, ends)
        ):

            cx = x + step * (i + 0.5)

            low = min(start, end)
            high = max(start, end)

            bar_y = py(low)
            bar_h = max(
                py(high) - py(low),
                1,
            )

            if value >= 0:
                fill = GREEN
            else:
                fill = RED

            c.setFillColor(fill)

            c.rect(
                cx - bar_w / 2,
                bar_y,
                bar_w,
                bar_h,
                fill=1,
                stroke=0,
            )

            # Connector to next bar.
            if i < len(values) - 1:

                next_cx = x + step * (i + 1.5)

                connector_y = py(end)

                c.setStrokeColor(
                    colors.HexColor("#B8C1CC")
                )

                c.setLineWidth(0.6)

                c.line(
                    cx + bar_w / 2,
                    connector_y,
                    next_cx - bar_w / 2,
                    connector_y,
                )

            # Value.
            c.setFillColor(DARK)
            c.setFont(
                "Helvetica-Bold",
                6.3,
            )

            text_y = (
                bar_y + bar_h + 3
                if value >= 0
                else bar_y - 9
            )

            c.drawCentredString(
                cx,
                text_y,
                f"{value:,.0f}",
            )

            c.setFont(
                "Helvetica",
                6,
            )

            c.drawCentredString(
                cx,
                y - 7,
                label,
            )

        # Final net cash flow bar.
        cx = x + step * 3.5

        net_low = min(
            0,
            net_value,
        )

        net_high = max(
            0,
            net_value,
        )

        c.setFillColor(
            NAVY
            if net_value >= 0
            else RED
        )

        c.rect(
            cx - bar_w / 2,
            py(net_low),
            bar_w,
            max(
                py(net_high) - py(net_low),
                1,
            ),
            fill=1,
            stroke=0,
        )

        c.setFillColor(DARK)
        c.setFont(
            "Helvetica-Bold",
            6.3,
        )

        c.drawCentredString(
            cx,
            py(net_high) + 3
            if net_value >= 0
            else py(net_low) - 9,
            f"{net_value:,.0f}",
        )

        c.setFont(
            "Helvetica",
            6,
        )

        c.drawCentredString(
            cx,
            y - 7,
            "Net Cash Flow",
        )

    return drawer


# ============================================================
# KPI TABLE
# ============================================================

def make_kpi_table(payload, width):

    styles = getSampleStyleSheet()

    label_style = ParagraphStyle(
        "KPI_Label",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=7.5,
        textColor=GREY,
        spaceAfter=0,
    )

    value_style = ParagraphStyle(
        "KPI_Value",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=12,
        textColor=NAVY,
        spaceBefore=2,
        spaceAfter=0,
    )

    items = [
        ("Revenue", fmt_cr(payload["latest_sales"])),
        ("Net Profit", fmt_cr(payload["latest_profit"])),
        ("ROE", fmt_pct(payload["latest_roe"])),
        ("ROCE", fmt_pct(payload["latest_roce"])),
        ("Debt / Equity", fmt_ratio(payload["latest_de"])),
        ("Free Cash Flow", fmt_cr(payload["latest_fcf"])),
    ]

    rows = []

    for row_index in range(2):

        row = []

        for col_index in range(3):

            label, value = items[
                row_index * 3 + col_index
            ]

            cell = Table(
                [
                    [
                        Paragraph(
                            label,
                            label_style,
                        )
                    ],
                    [
                        Paragraph(
                            value,
                            value_style,
                        )
                    ],
                ],
                colWidths=[
                    (width - 8 * mm) / 3
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
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            3 * mm,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            3 * mm,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, 0),
                            2 * mm,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, 0),
                            0.5 * mm,
                        ),
                        (
                            "TOPPADDING",
                            (0, 1),
                            (-1, 1),
                            0.5 * mm,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 1),
                            (-1, 1),
                            2.2 * mm,
                        ),
                    ]
                )
            )

            row.append(cell)

        rows.append(row)

    table = Table(
        rows,
        colWidths=[
            (width - 8 * mm) / 3
        ] * 3,
        rowHeights=[
            24 * mm,
            24 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
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
                    1.3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    1.3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1.3 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1.3 * mm,
                ),
            ]
        )
    )

    return table


# ============================================================
# SECTION HEADING
# ============================================================

def section_heading(
    text,
    width,
):

    style = ParagraphStyle(
        "SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=NAVY,
        spaceAfter=2 * mm,
        wordWrap="LTR",
    )

    return Paragraph(
        text,
        style,
    )


# ============================================================
# PROS / CONS
# ============================================================

def make_bullet_paragraphs(
    bullets,
    color,
):

    style = ParagraphStyle(
        f"Bullet_{color}",
        fontName="Helvetica",
        fontSize=6.4,
        leading=8.2,
        textColor=DARK,
        leftIndent=8,
        firstLineIndent=-6,
        spaceAfter=2.5,
        wordWrap="CJK",
    )

    output = []

    for text in bullets[:5]:

        output.append(
            Paragraph(
                f"• {str(text)}",
                style,
            )
        )

    if not output:
        output.append(
            Paragraph(
                "No generated signals available.",
                style,
            )
        )

    return output


def make_pros_cons(
    pros,
    cons,
    width,
):

    header_style = ParagraphStyle(
        "PCHeader",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9,
        textColor=WHITE,
    )

    pro_content = make_bullet_paragraphs(
        pros,
        GREEN,
    )

    con_content = make_bullet_paragraphs(
        cons,
        RED,
    )

    pro_cell = Table(
        [
            [
                Paragraph(
                    "PROS",
                    header_style,
                )
            ],
            [
                Table(
                    [[item] for item in pro_content],
                    colWidths=[
                        width / 2 - 7 * mm
                    ],
                    style=TableStyle(
                        [
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
                                0.7 * mm,
                            ),
                            (
                                "BOTTOMPADDING",
                                (0, 0),
                                (-1, -1),
                                0.7 * mm,
                            ),
                        ]
                    ),
                )
            ],
        ],
        colWidths=[
            width / 2 - 3 * mm
        ],
        style=TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    GREEN,
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    LIGHT_GREEN,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#B7DFC7"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, 0),
                    3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, 0),
                    3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    2 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    2 * mm,
                ),
            ]
        ),
    )

    con_cell = Table(
        [
            [
                Paragraph(
                    "CONS",
                    header_style,
                )
            ],
            [
                Table(
                    [[item] for item in con_content],
                    colWidths=[
                        width / 2 - 7 * mm
                    ],
                    style=TableStyle(
                        [
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
                                0.7 * mm,
                            ),
                            (
                                "BOTTOMPADDING",
                                (0, 0),
                                (-1, -1),
                                0.7 * mm,
                            ),
                        ]
                    ),
                )
            ],
        ],
        colWidths=[
            width / 2 - 3 * mm
        ],
        style=TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    RED,
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    LIGHT_RED,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#E6B8B8"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, 0),
                    3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, 0),
                    3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    2 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    2 * mm,
                ),
            ]
        ),
    )

    table = Table(
        [
            [
                pro_cell,
                con_cell,
            ]
        ],
        colWidths=[
            width / 2 - 1.5 * mm,
            width / 2 - 1.5 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    return table


# ============================================================
# CAPITAL ALLOCATION BADGE
# ============================================================

def make_capital_badge(
    label,
    width,
):

    style = ParagraphStyle(
        "CapitalBadge",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=NAVY,
    )

    small_style = ParagraphStyle(
        "CapitalSmall",
        fontName="Helvetica-Bold",
        fontSize=6.3,
        leading=7,
        textColor=GREY,
    )

    table = Table(
        [
            [
                Paragraph(
                    "CAPITAL ALLOCATION",
                    small_style,
                )
            ],
            [
                Paragraph(
                    label or "N/A",
                    style,
                )
            ],
        ],
        colWidths=[width],
        rowHeights=[
            7 * mm,
            10 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_BLUE,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#B8C9DC"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1.2 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1.2 * mm,
                ),
            ]
        )
    )

    return table


# ============================================================
# PDF DOCUMENT
# ============================================================

class TearsheetDoc(BaseDocTemplate):

    def __init__(
        self,
        filename,
        company_name,
        ticker,
    ):

        super().__init__(
            str(filename),
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=HEADER_H + 4 * mm,
            bottomMargin=BOTTOM_MARGIN,
            title=f"{company_name} Tearsheet",
            author="Nifty100 Financial Intelligence",
        )

        frame = Frame(
            MARGIN,
            BOTTOM_MARGIN,
            PAGE_W - 2 * MARGIN,
            PAGE_H - HEADER_H - BOTTOM_MARGIN - 6 * mm,
            id="main",
        )

        self.addPageTemplates(
            [
                PageTemplate(
                    id="main",
                    frames=[frame],
                    onPage=lambda c, d: draw_header(
                        c,
                        d,
                        company_name,
                        ticker,
                    ),
                )
            ]
        )


# ============================================================
# BUILD ONE TEARSHEET
# ============================================================

def build_tearsheet(
    company_id,
    output_path,
    data,
):

    payload = build_payload(
        data,
        company_id,
    )

    company_name, ticker = get_company_identity(
        data,
        company_id,
    )

    doc = TearsheetDoc(
        output_path,
        company_name,
        ticker,
    )

    usable_w = PAGE_W - 2 * MARGIN

    story = []

    # ========================================================
    # PAGE 1
    # ========================================================

    story.append(
        make_kpi_table(
            payload,
            usable_w,
        )
    )

    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    story.append(
        section_heading(
            "10-Year Revenue and Net Profit",
            usable_w,
        )
    )

    story.append(
        ChartBox(
            "",
            usable_w,
            68 * mm,
            draw_revenue_profit(
                payload["revenue"],
                payload["net_profit"],
                payload["revenue_years"],
            ),
        )
    )

    story.append(
        Spacer(
            1,
            3 * mm,
        )
    )

    story.append(
        section_heading(
            "ROE and ROCE Trend",
            usable_w,
        )
    )

    story.append(
        ChartBox(
            "",
            usable_w,
            60 * mm,
            draw_roe_roce(
                payload["trend_years"],
                payload["roe"],
                payload["roce"],
            ),
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # PAGE 2
    # ========================================================

    story.append(
        section_heading(
            "Balance Sheet Composition",
            usable_w,
        )
    )

    story.append(
        ChartBox(
            "",
            usable_w,
            61 * mm,
            draw_balance_sheet(
                payload["bs_years"],
                payload["equity"],
                payload["borrowings"],
                payload["other_liabilities"],
            ),
        )
    )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        section_heading(
            "Latest-Year Cash Flow",
            usable_w,
        )
    )

    story.append(
        ChartBox(
            "",
            usable_w,
            49 * mm,
            draw_waterfall(
                payload["latest_cfo"],
                payload["latest_cfi"],
                payload["latest_cff"],
                payload["latest_net_cash"],
            ),
        )
    )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        make_pros_cons(
            payload["pros"],
            payload["cons"],
            usable_w,
        )
    )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        make_capital_badge(
            payload["capital_pattern"],
            usable_w,
        )
    )

    doc.build(story)

    return Path(output_path)


# ============================================================
# TESTS
# ============================================================

TEST_COMPANIES = [
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "SUNPHARMA",
    "TATASTEEL",
]


def test_tearsheets(data):

    TEST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("\nDAY 33 TEARSHEET TEST")

    for company_id in TEST_COMPANIES:

        output_path = (
            TEST_DIR
            / f"{company_id}_tearsheet.pdf"
        )

        build_tearsheet(
            company_id,
            output_path,
            data,
        )

        reader = PdfReader(
            str(output_path)
        )

        pages = len(reader.pages)

        print(
            f"{company_id:10s} -> "
            f"{output_path.name} | "
            f"Pages: {pages}"
        )

        if pages != 2:
            raise RuntimeError(
                f"{company_id} tearsheet must have "
                f"exactly 2 pages; found {pages}"
            )

    print(
        f"\nAll {len(TEST_COMPANIES)} test companies "
        f"generated successfully."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("DAY 33 - PDF TEARSHEET TEMPLATE")
    print("=" * 60)

    data = load_data()

    print(
        f"Loaded P&L rows       : {len(data['pnl'])}"
    )

    print(
        f"Loaded balance rows   : {len(data['bs'])}"
    )

    print(
        f"Loaded cash-flow rows : {len(data['cf'])}"
    )

    print(
        f"Loaded ratio rows     : {len(data['ratios'])}"
    )

    print(
        f"Loaded pros/cons rows : {len(data['pros_cons'])}"
    )

    print(
        f"Loaded capital rows   : {len(data['capital'])}"
    )

    test_tearsheets(data)

    print("\nDay 33 test status: PASSED")


if __name__ == "__main__":
    main()