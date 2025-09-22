import sqlite3
from contextlib import contextmanager

DB_FILE = "bets.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
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

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE)
    yield conn
    conn.commit()
    conn.close()
