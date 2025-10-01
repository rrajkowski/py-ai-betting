import sqlite3
import os
from datetime import datetime

# Define the path to your database file (matching DB_PATH in db.py)
# os.path.dirname(__file__) gets the current directory (/scripts)
# os.path.join(..., "..", ...) moves up one level to the root directory
DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "bets.db"
)

TABLE_NAME = "ai_picks"


def get_db():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table_exists(conn):
    """
    Checks if the ai_picks table exists and creates it if it doesn't.
    This mimics the init_ai_picks() logic minimally required for insertion.
    """
    cur = conn.cursor()

    # NOTE: This definition must match the one in your app.db file exactly!
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT,
            sport TEXT,
            pick TEXT,
            market TEXT,
            line REAL,
            odds_american REAL,
            confidence TEXT,
            reasoning TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT
        )
    """)
    conn.commit()


def insert_mock_ai_picks(picks_data):
    """
    Inserts a list of dictionary-formatted AI picks directly into the ai_picks table.
    """
    conn = get_db()

    # CRITICAL: Ensure the table is created before trying to insert
    ensure_table_exists(conn)

    cur = conn.cursor()

    picks_to_insert = []
    for p in picks_data:
        picks_to_insert.append((
            p.get("game"), p.get("sport"), p.get("pick"), p.get("market"),
            p.get("line"), p.get("odds_american"), p.get("confidence"),
            p.get("reasoning"), p.get("date"), p.get("result")
        ))

    try:
        cur.executemany(f"""
            INSERT INTO {TABLE_NAME} (game, sport, pick, market, line, odds_american, confidence, reasoning, date, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, picks_to_insert)
        conn.commit()
        print(
            f"✅ Successfully inserted {len(picks_data)} mock picks into {TABLE_NAME}.")
    except sqlite3.OperationalError as e:
        print(f"❌ Database Error: {e}")
        print(f"Please ensure your '{TABLE_NAME}' table schema is correct.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        conn.close()


def main():
    """Defines the picks and runs the insertion."""

    # The DB_PATH needs to be correctly resolved based on running directory:
    # Running from /scripts/, moving up to find bets.db

    # Remove the redundant print as it's part of the insert function

    picks_to_insert = [
        {
            "game": "Cincinnati Bengals @ Denver Broncos",
            "sport": "NFL",
            "pick": "Denver Broncos",
            "market": "spreads",
            "line": -7.0,
            "odds_american": -115.0,
            "confidence": "3",
            "reasoning": "Historical data showed strong performance following a loss, and the line has high value.",
            "date": "2025-09-29T18:00:00",  # Specific time is optional, but date is key
            "result": "Win"  # Set to Win based on your scenario
        },
        {
            "game": "San Diego State vs Northern Illinois",
            "sport": "NCAAF",
            "pick": "Northern Illinois",
            "market": "spreads",
            "line": 1.5,  # Northern Illinois +1.5
            "odds_american": -110.0,
            "confidence": "2",
            "reasoning": "Northern Illinois defense keeps it within a field goal, providing coverage value.",
            "date": "2025-09-27T15:30:00",
            "result": "Loss"  # Set to Loss based on your scenario
        },
    ]

    insert_mock_ai_picks(picks_to_insert)


if __name__ == "__main__":
    main()
