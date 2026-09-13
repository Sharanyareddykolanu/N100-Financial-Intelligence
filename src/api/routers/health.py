import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]
DB_PATH = BASE_DIR / "nifty100.db"

START_TIME = time.time()
VERSION = "1.0.0"


def get_db_row_counts():

    connection = sqlite3.connect(DB_PATH)

    tables = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    counts = {}

    for (table_name,) in tables:

        count = connection.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        ).fetchone()[0]

        counts[table_name] = count

    connection.close()

    return counts


@router.get("/health")
def health_check():

    return {
        "status": "ok",
        "db_row_counts": get_db_row_counts(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "version": VERSION,
    }