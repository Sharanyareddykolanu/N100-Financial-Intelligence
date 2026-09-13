from pathlib import Path
import sqlite3
import csv

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"
STATS_FILE = ROOT / "output" / "portfolio_stats.csv"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/stats")
def get_portfolio_stats():
    """
    Return P10-P90 portfolio statistics for the 10 core KPIs.
    """

    if not STATS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Portfolio statistics file not found"
        )

    rows = []

    with open(STATS_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append({
                "KPI": row["KPI"],
                "P10": float(row["P10"]),
                "P25": float(row["P25"]),
                "P50": float(row["P50"]),
                "P75": float(row["P75"]),
                "P90": float(row["P90"]),
                "Mean": float(row["Mean"]),
                "Std": float(row["Std"]),
            })

    return {
        "company_count": 92,
        "kpi_count": len(rows),
        "statistics": rows
    }