# cleanup_picks.py

import sqlite3
import os

# Define the path to your database file
DB_PATH = "bets.db"


def delete_low_confidence_picks(conn):
    """Deletes rows with a confidence score of less than 2 or NULL."""
    print("Scanning for low-confidence picks...")
    cur = conn.cursor()

    # Use a single query to find and delete
    cur.execute(
        "DELETE FROM ai_picks WHERE confidence IS NULL OR CAST(confidence AS INTEGER) < 2")
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} low-confidence picks.")
    else:
        print("No low-confidence picks found.")


def delete_duplicate_picks(conn):
    """Deletes duplicate picks, keeping only the most recent entry for each unique bet."""
    print("\nScanning for duplicate picks...")
    cur = conn.cursor()

    # This query identifies duplicates based on market and team (pick), keeping only the latest entry.
    query = """
        DELETE FROM ai_picks
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM ai_picks
            GROUP BY market, pick
        )
    """
    cur.execute(query)
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} duplicate picks.")
    else:
        print("No duplicate picks found.")


def main():
    """Main function to run all cleanup tasks."""
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at '{DB_PATH}'")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Connected to database: {DB_PATH}\n")

        # Run all cleanup functions
        delete_low_confidence_picks(conn)
        delete_duplicate_picks(conn)

        print("\nDatabase cleanup complete!")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
