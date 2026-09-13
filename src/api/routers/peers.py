from pathlib import Path
import sqlite3

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/peers", tags=["Peers"])

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "nifty100.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/{group_name}")
def get_peer_group(group_name: str):
    """
    Return all companies in a peer group with
    percentile rank for each metric.
    """

    conn = get_connection()

    try:
        # Check whether the peer group exists.
        group = conn.execute(
            """
            SELECT DISTINCT peer_group_name
            FROM peer_percentiles
            WHERE LOWER(peer_group_name) = LOWER(?)
            """,
            (group_name,),
        ).fetchone()

        if group is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown peer group: {group_name}",
            )

        actual_group = group["peer_group_name"]

        rows = conn.execute(
            """
            SELECT
                company_id,
                peer_group_name,
                metric,
                value,
                percentile_rank,
                year
            FROM peer_percentiles
            WHERE LOWER(peer_group_name) = LOWER(?)
            ORDER BY company_id, metric, year
            """,
            (actual_group,),
        ).fetchall()

        companies = {}

        for row in rows:
            company_id = row["company_id"]

            if company_id not in companies:
                companies[company_id] = {
                    "company_id": company_id,
                    "peer_group_name": actual_group,
                    "year": row["year"],
                    "metrics": {},
                }

            metric_name = row["metric"]

            companies[company_id]["metrics"][metric_name] = {
                "value": row["value"],
                "percentile_rank": row["percentile_rank"],
            }

            # Keep the latest year available.
            if (
                row["year"] is not None
                and (
                    companies[company_id]["year"] is None
                    or row["year"] > companies[company_id]["year"]
                )
            ):
                companies[company_id]["year"] = row["year"]

        results = list(companies.values())

        return {
            "peer_group_name": actual_group,
            "company_count": len(results),
            "metric_count": 10,
            "metrics": [
                "Asset Turnover",
                "D/E",
                "EPS CAGR 5yr",
                "FCF",
                "Interest Coverage",
                "Net Profit Margin",
                "PAT CAGR 5yr",
                "ROCE",
                "ROE",
                "Revenue CAGR 5yr",
            ],
            "companies": results,
        }

    finally:
        conn.close()