"""Utility script to wipe all scraped data from the database.

Run this when you want a clean slate before a fresh scrape.
Works with both PostgreSQL (Supabase) and local SQLite.

Usage:
    python scripts/clear_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.db import _is_postgres, get_connection


def clear_all_data() -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if _is_postgres():
            cursor.execute("TRUNCATE TABLE tech_stack, job_classifications, posts CASCADE")
        else:
            cursor.execute("DELETE FROM tech_stack")
            cursor.execute("DELETE FROM job_classifications")
            cursor.execute("DELETE FROM posts")
        conn.commit()
        print("All data cleared successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    print("This will permanently delete ALL posts, classifications, and tech stack data.")
    answer = input("Type 'yes' to confirm: ").strip().lower()
    if answer == "yes":
        clear_all_data()
    else:
        print("Aborted — no data was changed.")
