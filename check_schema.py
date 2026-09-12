import sqlite3

c = sqlite3.connect("nifty100.db")

tables = c.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

for table in tables:
    print("\nTABLE:", table[0])
    print(c.execute(f"PRAGMA table_info({table[0]})").fetchall())

c.close()