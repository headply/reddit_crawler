"""Database connection and operations for PostgreSQL (production) / SQLite (local).

Configuration order:
  1. ``DATABASE_URL`` environment variable (loaded from `.env` via python-dotenv).
  2. Default: SQLite at ``data/reddit_jobs.db``.
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
    """Read DATABASE_URL from env, falling back to local SQLite."""
    url = os.getenv("DATABASE_URL")
    if url:
        logger.info("DATABASE_URL loaded from environment.")
        return url
    logger.info("No DATABASE_URL found; defaulting to local SQLite.")
    return _DEFAULT_DB_URL


DATABASE_URL: str = _resolve_database_url()


def _is_postgres() -> bool:
    """Check if the configured database is PostgreSQL."""
    return DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith(
        "postgres://"
    )


def get_connection(*, statement_timeout_ms: int = 30000):
    """Create and return a database connection.

    Returns PostgreSQL connection if DATABASE_URL is a postgres URI,
    otherwise falls back to SQLite for local development.

    The PostgreSQL connection is hardened against the failure mode that
    silently froze this pipeline for 5 days: a ``psycopg2.connect`` with no
    ``connect_timeout`` blocks forever when the database (or Supabase pooler)
    is unreachable or at its connection cap, and a process stuck in that
    blocking C call cannot even be killed by Airflow's SIGTERM. With these
    settings a stuck connection fails in seconds with a clear error instead.

    Args:
        statement_timeout_ms: Server-side ceiling on any single statement.
            Pass ``0`` to disable for genuinely long operations (e.g. a
            ``REFRESH MATERIALIZED VIEW CONCURRENTLY``).

    Raises:
        ConnectionError: If PostgreSQL connection fails with a helpful message.
    """
    if _is_postgres():
        import psycopg2
        import psycopg2.extras

        try:
            conn = psycopg2.connect(
                DATABASE_URL,
                connect_timeout=10,
                # TCP keepalives so a silently-dropped socket (NAT timeout,
                # pooler recycle) surfaces as an error instead of a hang.
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=3,
                # Server kills any statement exceeding this, so a stuck query
                # cannot wedge a worker thread indefinitely.
                options=f"-c statement_timeout={statement_timeout_ms}",
            )
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
        _apply_sqlite_v2_migrations(conn)
        conn.commit()
    finally:
        conn.close()


def _sqlite_column_exists(conn, table: str, column: str) -> bool:
    """Return True if the SQLite table already contains a column."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _sqlite_add_column_if_missing(conn, table: str, ddl: str) -> None:
    """Add a column to a SQLite table if it does not exist."""
    col_name = ddl.split()[0]
    if not _sqlite_column_exists(conn, table, col_name):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _apply_sqlite_v2_migrations(conn) -> None:
    """Apply SQLite-compatible schema updates for v2 features."""
    _sqlite_add_column_if_missing(conn, "posts", "content_hash TEXT")
    _sqlite_add_column_if_missing(conn, "posts", "title_tokens TEXT")
    _sqlite_add_column_if_missing(conn, "posts", "dedup_status TEXT DEFAULT 'unique'")
    _sqlite_add_column_if_missing(conn, "posts", "canonical_post_id TEXT")
    _sqlite_add_column_if_missing(conn, "posts", "raw_body_purged_at TIMESTAMP")

    _sqlite_add_column_if_missing(conn, "job_classifications", "industry_vertical TEXT")
    _sqlite_add_column_if_missing(conn, "job_classifications", "company_stage TEXT")
    _sqlite_add_column_if_missing(conn, "job_classifications", "compensation_min INTEGER")
    _sqlite_add_column_if_missing(conn, "job_classifications", "compensation_max INTEGER")
    _sqlite_add_column_if_missing(conn, "job_classifications", "compensation_currency TEXT")
    _sqlite_add_column_if_missing(conn, "job_classifications", "compensation_period TEXT")
    _sqlite_add_column_if_missing(conn, "job_classifications", "equity_mentioned BOOLEAN DEFAULT 0")
    _sqlite_add_column_if_missing(conn, "job_classifications", "is_scam BOOLEAN DEFAULT 0")
    _sqlite_add_column_if_missing(conn, "job_classifications", "scam_reasons TEXT")
    _sqlite_add_column_if_missing(conn, "job_classifications", "post_category TEXT")

    conn.execute(
        """CREATE TABLE IF NOT EXISTS subreddit_health (
               subreddit TEXT NOT NULL,
               date DATE NOT NULL,
               posts_scraped INTEGER DEFAULT 0,
               jobs_found INTEGER DEFAULT 0,
               scams_flagged INTEGER DEFAULT 0,
               dedup_rate REAL,
               PRIMARY KEY (subreddit, date)
           )"""
    )


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
        if fetch and _is_postgres():
            import psycopg2.extras

            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
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


_POST_COLUMNS = (
    "post_id", "title", "body", "author", "subreddit",
    "score", "num_comments", "created_utc", "post_url",
)


def insert_posts_bulk(posts: list[dict[str, Any]]) -> int:
    """Insert many posts over a single connection, skipping duplicates.

    Replaces the previous one-connection-per-post pattern, which opened a
    fresh connection for every row and — under 8 concurrent scraper threads —
    churned through (and exhausted) the database/pooler connection cap. Here a
    whole subreddit's posts go in over one connection in one round trip.

    Returns:
        Number of rows actually inserted (duplicates are ignored).
    """
    if not posts:
        return 0

    rows = [tuple(p[col] for col in _POST_COLUMNS) for p in posts]
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if _is_postgres():
            from psycopg2.extras import execute_values

            execute_values(
                cursor,
                f"""INSERT INTO posts ({", ".join(_POST_COLUMNS)})
                    VALUES %s
                    ON CONFLICT (post_id) DO NOTHING""",
                rows,
            )
            inserted = cursor.rowcount
        else:
            before = conn.total_changes
            cursor.executemany(
                f"""INSERT OR IGNORE INTO posts ({", ".join(_POST_COLUMNS)})
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            inserted = conn.total_changes - before
        conn.commit()
        return inserted
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
                    work_mode, sentiment_score, urgency_score,
                    confidence, llm_classified, industry_vertical,
                    company_stage, compensation_min, compensation_max,
                    compensation_currency, compensation_period,
                    equity_mentioned, is_scam, scam_reasons, post_category)
                   VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph},
                           {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                   ON CONFLICT (post_id)
                   DO UPDATE SET is_job = EXCLUDED.is_job,
                                 job_type = EXCLUDED.job_type,
                                 seniority = EXCLUDED.seniority,
                                 domain = EXCLUDED.domain,
                                 work_mode = EXCLUDED.work_mode,
                                 sentiment_score = EXCLUDED.sentiment_score,
                                 urgency_score = EXCLUDED.urgency_score,
                                 confidence = EXCLUDED.confidence,
                                 llm_classified = EXCLUDED.llm_classified,
                                 industry_vertical = EXCLUDED.industry_vertical,
                                 company_stage = EXCLUDED.company_stage,
                                 compensation_min = EXCLUDED.compensation_min,
                                 compensation_max = EXCLUDED.compensation_max,
                                 compensation_currency = EXCLUDED.compensation_currency,
                                 compensation_period = EXCLUDED.compensation_period,
                                 equity_mentioned = EXCLUDED.equity_mentioned,
                                 is_scam = EXCLUDED.is_scam,
                                 scam_reasons = EXCLUDED.scam_reasons,
                                 post_category = EXCLUDED.post_category,
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
                    classification.get("confidence"),
                    classification.get("llm_classified", False),
                    classification.get("industry_vertical"),
                    classification.get("company_stage"),
                    classification.get("compensation_min"),
                    classification.get("compensation_max"),
                    classification.get("compensation_currency"),
                    classification.get("compensation_period"),
                    classification.get("equity_mentioned"),
                    classification.get("is_scam"),
                    classification.get("scam_reasons"),
                    classification.get("post_category"),
                ),
            )
        else:
            cursor.execute(
                """INSERT OR REPLACE INTO job_classifications
                   (post_id, is_job, job_type, seniority, domain,
                    work_mode, sentiment_score, urgency_score,
                    confidence, llm_classified, industry_vertical,
                    company_stage, compensation_min, compensation_max,
                    compensation_currency, compensation_period,
                    equity_mentioned, is_scam, scam_reasons, post_category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    classification["post_id"],
                    classification["is_job"],
                    classification.get("job_type"),
                    classification.get("seniority"),
                    classification.get("domain"),
                    classification.get("work_mode"),
                    classification.get("sentiment_score"),
                    classification.get("urgency_score"),
                    classification.get("confidence"),
                    classification.get("llm_classified", False),
                    classification.get("industry_vertical"),
                    classification.get("company_stage"),
                    classification.get("compensation_min"),
                    classification.get("compensation_max"),
                    classification.get("compensation_currency"),
                    classification.get("compensation_period"),
                    classification.get("equity_mentioned"),
                    classification.get("is_scam"),
                    classification.get("scam_reasons"),
                    classification.get("post_category"),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def refresh_views() -> dict[str, int]:
    """Refresh materialized views and update subreddit health metrics."""
    if not _is_postgres():
        logger.info("Skipping materialized view refresh on SQLite.")
        return {"refreshed": 0}

    views = [
        "mv_skill_demand_weekly",
        "mv_domain_volume_weekly",
        "mv_compensation_by_role",
        "mv_subreddit_quality",
    ]
    # Materialized view refreshes legitimately run longer than the default
    # 30s statement timeout, so disable it for this connection only.
    conn = get_connection(statement_timeout_ms=0)
    try:
        conn.autocommit = True
        cursor = conn.cursor()
        _update_subreddit_health(cursor)
        refreshed = 0
        for view in views:
            try:
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
                refreshed += 1
            except Exception as exc:
                logger.warning("Failed to refresh %s: %s", view, exc)
        return {"refreshed": refreshed}
    finally:
        conn.close()


def _update_subreddit_health(cursor) -> None:
    """Upsert daily subreddit health metrics (PostgreSQL only)."""
    cursor.execute(
        """INSERT INTO subreddit_health
           (subreddit, date, posts_scraped, jobs_found, scams_flagged, dedup_rate)
           SELECT
               p.subreddit,
               CURRENT_DATE AS date,
               COUNT(*) AS posts_scraped,
               SUM(CASE WHEN jc.is_job THEN 1 ELSE 0 END) AS jobs_found,
               SUM(CASE WHEN COALESCE(jc.is_scam, FALSE) THEN 1 ELSE 0 END) AS scams_flagged,
               SUM(CASE WHEN COALESCE(p.dedup_status, 'unique') != 'unique' THEN 1 ELSE 0 END)::float
               / NULLIF(COUNT(*), 0) AS dedup_rate
           FROM posts p
           LEFT JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE p.scraped_at::date = CURRENT_DATE
           GROUP BY p.subreddit
           ON CONFLICT (subreddit, date)
           DO UPDATE SET
               posts_scraped = EXCLUDED.posts_scraped,
               jobs_found = EXCLUDED.jobs_found,
               scams_flagged = EXCLUDED.scams_flagged,
               dedup_rate = EXCLUDED.dedup_rate"""
    )


def cleanup_old_raw() -> int:
    """Clear raw post bodies older than 90 days and set purge timestamp."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if _is_postgres():
            cursor.execute(
                """UPDATE posts
                   SET body = NULL,
                       raw_body_purged_at = NOW()
                   WHERE created_utc < NOW() - INTERVAL '90 days'
                     AND raw_body_purged_at IS NULL"""
            )
        else:
            cursor.execute(
                """UPDATE posts
                   SET body = NULL,
                       raw_body_purged_at = CURRENT_TIMESTAMP
                   WHERE created_utc < datetime('now', '-90 days')
                     AND raw_body_purged_at IS NULL"""
            )
        conn.commit()
        return cursor.rowcount
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
