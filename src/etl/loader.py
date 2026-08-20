import sqlite3


def get_connection(db_path="nifty100.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(
    db_path="nifty100.db",
    schema_path="database/schema.sql"
):
    conn = get_connection(db_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    conn.executescript(schema)
    conn.commit()

    return conn