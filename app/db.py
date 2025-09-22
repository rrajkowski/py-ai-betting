import sqlite3
import os

DB_PATH = os.getenv("SQLITE_DB_PATH", "bets.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            match TEXT,
            bet_type TEXT,
            odds REAL,
            stake REAL,
            probability REAL,
            raw_output TEXT,
            outcome TEXT,
            profit REAL,
            expected_value REAL
        )
    """)
    conn.commit()
    conn.close()
