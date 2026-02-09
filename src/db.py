"""Database connection and initialization utilities.

Handles SQLite (local dev) and PostgreSQL (production) connections,
schema creation, and common database operations.
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/reddit_jobs.db")
SCHEMA_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection.

    Returns:
        sqlite3.Connection: Active database connection with row factory set.
    """
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Initialize the database by executing the schema SQL file."""
    conn = get_connection()
    try:
        schema_sql = SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def execute_query(
    query: str,
    params: Optional[tuple[Any, ...]] = None,
    fetch: bool = False,
) -> list[sqlite3.Row]:
    """Execute a SQL query and optionally fetch results.

    Args:
        query: SQL query string.
        params: Optional tuple of query parameters.
        fetch: Whether to fetch and return results.

    Returns:
        List of rows if fetch is True, empty list otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(query, params or ())
        if fetch:
            results = cursor.fetchall()
        else:
            results = []
        conn.commit()
        return results
    finally:
        conn.close()


def insert_post(post_data: dict[str, Any]) -> bool:
    """Insert a scraped post into the database, skipping duplicates.

    Args:
        post_data: Dictionary containing post fields.

    Returns:
        True if inserted, False if duplicate.
    """
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO posts
               (post_id, title, body, author, subreddit, score,
                num_comments, created_utc, post_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                post_data["post_id"],
                post_data["title"],
                post_data["body"],
                post_data["author"],
                post_data["subreddit"],
                post_data["score"],
                post_data["num_comments"],
                post_data["created_utc"],
                post_data["post_url"],
            ),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def insert_classification(classification: dict[str, Any]) -> None:
    """Insert or update a job classification for a post.

    Args:
        classification: Dictionary containing classification fields.
    """
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO job_classifications
               (post_id, is_job, job_type, seniority, domain,
                work_mode, sentiment_score, urgency_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                classification["post_id"],
                classification["is_job"],
                classification.get("job_type"),
                classification.get("seniority"),
                classification.get("domain"),
                classification.get("work_mode"),
                classification.get("sentiment_score"),
                classification.get("urgency_score"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_tech_stack(post_id: str, technologies: list[str]) -> None:
    """Insert tech stack entries for a post.

    Args:
        post_id: Reddit post ID.
        technologies: List of technology names detected.
    """
    conn = get_connection()
    try:
        for tech in technologies:
            conn.execute(
                "INSERT OR IGNORE INTO tech_stack (post_id, technology) VALUES (?, ?)",
                (post_id, tech),
            )
        conn.commit()
    finally:
        conn.close()
