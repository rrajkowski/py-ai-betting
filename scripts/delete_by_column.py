# cleanup_missing_data.py

import sqlite3
import os

# --- Configuration ---
DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "bets.db"
)
TABLE_NAME = "ai_picks"
COLUMN_TO_CLEAN = "date"  # column to check
# value that indicates missing data
VALUE_TO_CLEAN = ""


def delete_rows_with_missing_data(table: str, column: str, value: str):
    """
    Deletes all rows from a table where a specific column's value matches VALUE_TO_CLEAN.
    Includes a confirmation step for safety.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at '{DB_PATH}'")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Count rows first
        count_query = f"SELECT COUNT(*) FROM {table} WHERE {column} = ?"
        cur.execute(count_query, (value,))
        count = cur.fetchone()[0]

        if count == 0:
            print(
                f"No rows found in '{table}' where '{column}' = '{value}'. Nothing to delete.")
            return

        print(f"Found {count} rows in '{table}' where '{column}' = '{value}'.")
        confirm = input(
            "Are you sure you want to permanently delete these rows? (y/n): ")

        if confirm.lower() != 'y':
            print("Deletion cancelled by user.")
            return

        # Perform deletion
        delete_query = f"DELETE FROM {table} WHERE {column} = ?"
        cur.execute(delete_query, (value,))
        deleted_count = cur.rowcount
        conn.commit()

        print(f"✅ Success! Deleted {deleted_count} rows.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print(
        f"--- Preparing to delete rows from '{TABLE_NAME}' where '{COLUMN_TO_CLEAN}' = '{VALUE_TO_CLEAN}' ---"
    )
    delete_rows_with_missing_data(TABLE_NAME, COLUMN_TO_CLEAN, VALUE_TO_CLEAN)
