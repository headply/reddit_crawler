"""Tests for the database module."""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

# Set test database before importing db module
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"

from src.db import (
    get_connection,
    init_db,
    insert_classification,
    insert_post,
    insert_tech_stack,
    execute_query,
)


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh test database for each test."""
    # Re-create tables
    init_db()
    yield
    # Clean up tables after each test
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tech_stack")
        conn.execute("DELETE FROM job_classifications")
        conn.execute("DELETE FROM posts")
        conn.commit()
    finally:
        conn.close()


SAMPLE_POST = {
    "post_id": "abc123",
    "title": "[Hiring] Senior Python Developer - Remote",
    "body": "We are looking for a senior Python developer...",
    "author": "test_user",
    "subreddit": "forhire",
    "score": 42,
    "num_comments": 10,
    "created_utc": "2025-01-01T00:00:00+00:00",
    "post_url": "https://www.reddit.com/r/forhire/comments/abc123",
}


class TestDatabase:
    """Tests for database operations."""

    def test_init_db_creates_tables(self):
        """Tables should exist after init_db."""
        conn = get_connection()
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            table_names = {row["name"] for row in tables}
            assert "posts" in table_names
            assert "job_classifications" in table_names
            assert "tech_stack" in table_names
        finally:
            conn.close()

    def test_insert_post(self):
        """Should insert a post and return True."""
        result = insert_post(SAMPLE_POST)
        assert result is True

        rows = execute_query(
            "SELECT * FROM posts WHERE post_id = ?",
            ("abc123",),
            fetch=True,
        )
        assert len(rows) == 1
        assert rows[0]["title"] == SAMPLE_POST["title"]

    def test_insert_duplicate_post(self):
        """Should skip duplicate posts."""
        insert_post(SAMPLE_POST)
        result = insert_post(SAMPLE_POST)
        # Second insert should not create a new row
        rows = execute_query("SELECT * FROM posts", fetch=True)
        assert len(rows) == 1

    def test_insert_classification(self):
        """Should insert a classification for a post."""
        insert_post(SAMPLE_POST)
        classification = {
            "post_id": "abc123",
            "is_job": True,
            "job_type": "Full-time",
            "seniority": "Senior",
            "domain": "Software",
            "work_mode": "Remote",
            "sentiment_score": 0.5,
            "urgency_score": 0.3,
        }
        insert_classification(classification)

        rows = execute_query(
            "SELECT * FROM job_classifications WHERE post_id = ?",
            ("abc123",),
            fetch=True,
        )
        assert len(rows) == 1
        assert rows[0]["domain"] == "Software"

    def test_insert_tech_stack(self):
        """Should insert tech stack entries for a post."""
        insert_post(SAMPLE_POST)
        insert_tech_stack("abc123", ["Python", "AWS", "Docker"])

        rows = execute_query(
            "SELECT technology FROM tech_stack WHERE post_id = ?",
            ("abc123",),
            fetch=True,
        )
        techs = {row["technology"] for row in rows}
        assert techs == {"Python", "AWS", "Docker"}

    def test_insert_tech_stack_no_duplicates(self):
        """Should not insert duplicate tech stack entries."""
        insert_post(SAMPLE_POST)
        insert_tech_stack("abc123", ["Python", "Python", "AWS"])
        insert_tech_stack("abc123", ["Python"])

        rows = execute_query(
            "SELECT technology FROM tech_stack WHERE post_id = ?",
            ("abc123",),
            fetch=True,
        )
        assert len(rows) == 2  # Python + AWS

    def test_execute_query_fetch(self):
        """execute_query with fetch should return results."""
        insert_post(SAMPLE_POST)
        rows = execute_query("SELECT COUNT(*) as cnt FROM posts", fetch=True)
        assert rows[0]["cnt"] == 1
