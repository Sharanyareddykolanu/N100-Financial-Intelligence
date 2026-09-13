import sqlite3
import time
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    companies,
    screener,
    sectors,
    peers,
    valuation,
    portfolio,
    documents,
    health,
)

# ============================================================
# DAY 38 - FASTAPI SERVER
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "nifty100.db"

VERSION = "1.0.0"
START_TIME = time.time()

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("nifty100-api")


# ------------------------------------------------------------
# SQLite connection
# ------------------------------------------------------------

def get_db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# ------------------------------------------------------------
# FastAPI application
# ------------------------------------------------------------

app = FastAPI(
    title="Nifty100 Financial Intelligence API",
    version=VERSION,
    description="FastAPI server for Nifty100 financial analytics.",
)


# ------------------------------------------------------------
# CORS - Internal use only
# ------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# Request logging middleware
# ------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):

    start_time = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start_time

    logger.info(
        "%s %s - %.4f seconds",
        request.method,
        request.url.path,
        elapsed,
    )

    return response


# ------------------------------------------------------------
# Routers
# ------------------------------------------------------------

app.include_router(companies.router, prefix="/api/v1")
app.include_router(screener.router, prefix="/api/v1")
app.include_router(sectors.router, prefix="/api/v1")
app.include_router(peers.router, prefix="/api/v1")
app.include_router(valuation.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "Nifty100 Financial Intelligence API",
        "version": VERSION,
    }