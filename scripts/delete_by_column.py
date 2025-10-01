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
COLUMN_TO_CLEAN = "sport"  # Set the column you want to check for missing values


def delete_rows_with_missing_data(table: str, column: str):
    """
    Deletes all rows from a table where a specific column's value is NULL or empty.
    Includes a confirmation step for safety.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at '{DB_PATH}'")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Build queries safely. Using f-strings here is safe as table/column names are not user-injected.
        count_query = f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL OR {column} = ''"
        delete_query = f"DELETE FROM {table} WHERE {column} IS NULL OR {column} = ''"

        # 1. Safety Check: Count the rows first
        cur.execute(count_query)
        count = cur.fetchone()[0]

        if count == 0:
            print(
                f"No rows found in '{table}' with a missing '{column}' value. Nothing to delete.")
            return

        # 2. Ask for user confirmation
        print(
            f"Found {count} rows in '{table}' with a missing '{column}' value.")
        confirm = input(
            "Are you sure you want to permanently delete these rows? (y/n): ")

        if confirm.lower() != 'y':
            print("Deletion cancelled by user.")
            return

        # 3. Execute the DELETE statement
        cur.execute(delete_query)
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
        f"--- Preparing to delete rows from '{TABLE_NAME}' where '{COLUMN_TO_CLEAN}' is missing ---")
    delete_rows_with_missing_data(TABLE_NAME, COLUMN_TO_CLEAN)
