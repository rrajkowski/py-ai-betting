# cleanup_picks.py

import sqlite3
import os

# Define the path to your database file
DB_PATH = "bets.db"


def delete_low_confidence_picks():
    """
    Connects to the SQLite database and deletes rows from the ai_picks table
    that have a confidence score of less than 2 or no confidence score.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at '{DB_PATH}'")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # First, count the rows that will be deleted
        cur.execute(
            "SELECT COUNT(*) FROM ai_picks WHERE confidence IS NULL OR CAST(confidence AS INTEGER) < 2")
        count_to_delete = cur.fetchone()[0]

        if count_to_delete == 0:
            print("No low-confidence picks found to delete. Your table is already clean!")
            return

        print(
            f"Found {count_to_delete} picks with confidence less than 2 or missing. Deleting them now...")

        # Execute the DELETE statement
        cur.execute(
            "DELETE FROM ai_picks WHERE confidence IS NULL OR CAST(confidence AS INTEGER) < 2")

        # 'cur.rowcount' will hold the number of rows affected by the last query
        deleted_count = cur.rowcount

        conn.commit()
        print(
            f"✅ Success! Deleted {deleted_count} rows from the ai_picks table.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    delete_low_confidence_picks()
