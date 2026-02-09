"""Database connection and operations for PostgreSQL (Supabase).

Handles PostgreSQL connections via psycopg2 and common database operations.
Falls back to SQLite for local development if DATABASE_URL starts with 'sqlite'.

Supports configuration via:
  1. Streamlit secrets (st.secrets["DATABASE_URL"]) — for Streamlit Cloud
  2. Environment variables (os.getenv) — for GitHub Actions / containers
  3. .env file (python-dotenv) — for local development
  4. Default: SQLite at data/reddit_jobs.db
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_DB_URL = "sqlite:///data/reddit_jobs.db"
SCHEMA_PATH: Path = Path(__file__).resolve().parent.parent / "data" / "schema.sql"


def _resolve_database_url() -> str:
    """Resolve the database URL from available configuration sources.

    Priority:
        1. Streamlit secrets (st.secrets)
        2. OS environment variable
        3. Default SQLite path

    Returns:
        Database connection URL string.
    """
    # 1. Try Streamlit secrets first (works on Streamlit Cloud)
    try:
        import streamlit as st

        url = st.secrets.get("DATABASE_URL")
        if url:
            logger.info("DATABASE_URL loaded from Streamlit secrets.")
            return url
    except (ImportError, AttributeError, FileNotFoundError):
        pass

    # 2. Fall back to OS environment variable (.env already loaded above)
    url = os.getenv("DATABASE_URL")
    if url:
        logger.info("DATABASE_URL loaded from environment variable.")
        return url

    # 3. Default to local SQLite
    logger.info("No DATABASE_URL found; defaulting to local SQLite.")
    return _DEFAULT_DB_URL


DATABASE_URL: str = _resolve_database_url()


def _is_postgres() -> bool:
    """Check if the configured database is PostgreSQL."""
    return DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith(
        "postgres://"
    )


def get_connection():
    """Create and return a database connection.

    Returns PostgreSQL connection if DATABASE_URL is a postgres URI,
    otherwise falls back to SQLite for local development.

    Raises:
        ConnectionError: If PostgreSQL connection fails with a helpful message.
    """
    if _is_postgres():
        import psycopg2
        import psycopg2.extras

        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            return conn
        except psycopg2.OperationalError as e:
            logger.error("Failed to connect to PostgreSQL: %s", e)
            raise ConnectionError(
                "Could not connect to PostgreSQL. Please verify:\n"
                "  1. DATABASE_URL is correct in your Streamlit secrets or .env\n"
                "  2. The PostgreSQL server is running and reachable\n"
                "  3. Your credentials (user/password) are valid\n"
                "  4. The database exists and accepts connections\n\n"
                f"Current DATABASE_URL starts with: {DATABASE_URL[:25]}...\n\n"
                f"Original error: {e}"
            ) from e
    else:
        import sqlite3

        db_path = DATABASE_URL.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def init_db() -> None:
    """Initialize the database by executing the schema SQL file.

    For PostgreSQL (Supabase), the schema should already be created
    via the Supabase SQL Editor. This is mainly for SQLite local dev.
    """
    if _is_postgres():
        # Schema is managed via Supabase dashboard / migrations
        return

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
) -> list:
    """Execute a SQL query and optionally fetch results.

    Args:
        query: SQL query string (use %s placeholders for PostgreSQL).
        params: Optional tuple of query parameters.
        fetch: Whether to fetch and return results.

    Returns:
        List of rows if fetch is True, empty list otherwise.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        if fetch:
            results = cursor.fetchall()
        else:
            results = []
        conn.commit()
        return results
    finally:
        conn.close()


def _placeholder() -> str:
    """Return the correct SQL placeholder for the current database."""
    return "%s" if _is_postgres() else "?"


def insert_post(post_data: dict[str, Any]) -> bool:
    """Insert a scraped post into the database, skipping duplicates.

    Args:
        post_data: Dictionary containing post fields.

    Returns:
        True if inserted, False if duplicate.
    """
    ph = _placeholder()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if _is_postgres():
            cursor.execute(
                f"""INSERT INTO posts
                   (post_id, title, body, author, subreddit, score,
                    num_comments, created_utc, post_url)
                   VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                   ON CONFLICT (post_id) DO NOTHING""",
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
        else:
            cursor.execute(
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
        return cursor.rowcount > 0
    finally:
        conn.close()


def insert_classification(classification: dict[str, Any]) -> None:
    """Insert or update a job classification for a post."""
    ph = _placeholder()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if _is_postgres():
            cursor.execute(
                f"""INSERT INTO job_classifications
                   (post_id, is_job, job_type, seniority, domain,
                    work_mode, sentiment_score, urgency_score)
                   VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                   ON CONFLICT (post_id)
                   DO UPDATE SET is_job = EXCLUDED.is_job,
                                 job_type = EXCLUDED.job_type,
                                 seniority = EXCLUDED.seniority,
                                 domain = EXCLUDED.domain,
                                 work_mode = EXCLUDED.work_mode,
                                 sentiment_score = EXCLUDED.sentiment_score,
                                 urgency_score = EXCLUDED.urgency_score,
                                 classified_at = NOW()""",
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
        else:
            cursor.execute(
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
    """Insert tech stack entries for a post."""
    ph = _placeholder()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for tech in technologies:
            if _is_postgres():
                cursor.execute(
                    f"INSERT INTO tech_stack (post_id, technology) VALUES ({ph}, {ph}) ON CONFLICT DO NOTHING",
                    (post_id, tech),
                )
            else:
                cursor.execute(
                    "INSERT OR IGNORE INTO tech_stack (post_id, technology) VALUES (?, ?)",
                    (post_id, tech),
                )
        conn.commit()
    finally:
        conn.close()