# cleanup_picks.py

import sqlite3
import os

# Define the path to your database file
DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "bets.db"
)
TABLE_NAME = "ai_picks"


def delete_low_confidence_picks(conn):
    """Deletes rows with a confidence score of less than 2 or NULL."""
    print("Scanning for low-confidence picks...")
    cur = conn.cursor()

    # Use a single query to find and delete
    cur.execute(
        f"DELETE FROM {TABLE_NAME} WHERE confidence IS NULL OR CAST(confidence AS INTEGER) < 2")
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} low-confidence picks.")
    else:
        print("No low-confidence picks found.")


def delete_duplicate_picks(conn):
    """Deletes duplicate picks, keeping only the most recent entry per market/pick by date."""
    print("\nScanning for duplicate picks...")
    cur = conn.cursor()

    # Delete all but the latest by date for each market/pick
    query = f"""
        DELETE FROM {TABLE_NAME}
        WHERE id NOT IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY market, pick
                           ORDER BY date DESC
                       ) AS rn
                FROM {TABLE_NAME}
            ) ranked
            WHERE rn = 1
        )
    """
    cur.execute(query)
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(
            f"✅ Deleted {deleted_count} duplicate picks (kept latest by date).")
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
