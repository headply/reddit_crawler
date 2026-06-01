"""Tests for the deduplication module."""

from __future__ import annotations

import os
import tempfile

import pytest

_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_test_db.name}")

from src.db import get_connection, init_db, insert_post
from src.dedupe import (
    _build_clusters,
    _content_hash,
    _jaccard,
    _normalize,
    _title_tokens,
    run_dedup,
)


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh test database for each test."""
    init_db()
    yield
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tech_stack")
        conn.execute("DELETE FROM job_classifications")
        conn.execute("DELETE FROM posts")
        conn.commit()
    finally:
        conn.close()


def _make_post(post_id: str, title: str, body: str = "") -> dict:
    return {
        "post_id": post_id,
        "title": title,
        "body": body,
        "author": "tester",
        "subreddit": "forhire",
        "score": 1,
        "num_comments": 0,
        "created_utc": "2025-01-01T00:00:00+00:00",
        "post_url": f"https://reddit.com/r/forhire/{post_id}",
        "scraped_at": "2025-01-01T00:00:00+00:00",
        "flair": None,
    }


# ---------------------------------------------------------------------------
# Unit tests — pure functions
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_lowercases(self):
        assert _normalize("HELLO World") == "hello world"

    def test_strips_urls(self):
        result = _normalize("Check https://example.com for details")
        assert "https" not in result
        assert "example.com" not in result

    def test_strips_markdown(self):
        result = _normalize("**bold** and _italic_")
        assert "**" not in result
        assert "_" not in result

    def test_collapses_whitespace(self):
        result = _normalize("  too   many   spaces  ")
        assert result == "too many spaces"


class TestTitleTokens:
    def test_returns_space_separated_lowercase(self):
        result = _title_tokens("Hiring Python Dev")
        assert result == "hiring python dev"

    def test_strips_non_alphanumeric(self):
        result = _title_tokens("[Hiring] Senior Dev!")
        assert "[" not in result
        assert "!" not in result
        assert "hiring" in result
        assert "senior" in result

    def test_empty_string(self):
        assert _title_tokens("") == ""


class TestContentHash:
    def test_identical_content_same_hash(self):
        h1 = _content_hash("Hiring Python Dev", "We need a dev")
        h2 = _content_hash("Hiring Python Dev", "We need a dev")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = _content_hash("Hiring Python Dev", "We need a dev")
        h2 = _content_hash("Hiring JS Dev", "We need a dev")
        assert h1 != h2

    def test_normalizes_before_hashing(self):
        h1 = _content_hash("HIRING python dev", "we need a dev")
        h2 = _content_hash("hiring python dev", "we need a dev")
        assert h1 == h2

    def test_returns_hex_string(self):
        h = _content_hash("Test", "body")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestJaccard:
    def test_identical_sets(self):
        tokens = ["python", "developer", "remote"]
        assert _jaccard(tokens, tokens) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard(["python"], ["java"]) == 0.0

    def test_partial_overlap(self):
        a = ["senior", "python", "developer"]
        b = ["senior", "python", "engineer"]
        sim = _jaccard(a, b)
        # intersection={senior,python}, union={senior,python,developer,engineer} → 2/4=0.5
        assert sim == pytest.approx(0.5)

    def test_empty_list_returns_zero(self):
        assert _jaccard([], ["python"]) == 0.0
        assert _jaccard(["python"], []) == 0.0


class TestBuildClusters:
    def test_simple_pair(self):
        clusters = _build_clusters([("a", "b")])
        assert len(clusters) == 1
        assert {"a", "b"} in clusters

    def test_chain_merges(self):
        # a-b and b-c should all end up in one cluster
        clusters = _build_clusters([("a", "b"), ("b", "c")])
        assert len(clusters) == 1
        assert {"a", "b", "c"} in clusters

    def test_two_independent_pairs(self):
        clusters = _build_clusters([("a", "b"), ("c", "d")])
        assert len(clusters) == 2

    def test_empty_pairs(self):
        assert _build_clusters([]) == []

    def test_single_node_not_in_cluster(self):
        # Only multi-member clusters are returned
        clusters = _build_clusters([("a", "b")])
        for cluster in clusters:
            assert len(cluster) > 1


# ---------------------------------------------------------------------------
# Integration tests — run_dedup() against SQLite
# ---------------------------------------------------------------------------

class TestRunDedup:
    def test_exact_duplicate_flagged(self):
        insert_post(_make_post("post1", "Hiring Python Dev", "We need a Python dev ASAP"))
        insert_post(_make_post("post2", "Hiring Python Dev", "We need a Python dev ASAP"))

        result = run_dedup()
        assert result["hashes_updated"] >= 2
        assert result["exact_reposts"] >= 1

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT post_id, dedup_status FROM posts ORDER BY post_id"
            )
            rows = {r[0]: r[1] for r in cursor.fetchall()}
        finally:
            conn.close()

        statuses = set(rows.values())
        assert "exact_repost" in statuses
        assert "unique" in statuses

    def test_unique_post_stays_unique(self):
        insert_post(_make_post("post3", "Hiring Python Dev", "Looking for Python"))
        insert_post(_make_post("post4", "Hiring Java Dev", "Looking for Java"))

        run_dedup()

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT dedup_status FROM posts")
            statuses = [r[0] for r in cursor.fetchall()]
        finally:
            conn.close()

        assert all(s == "unique" for s in statuses)

    def test_run_dedup_is_idempotent(self):
        insert_post(_make_post("post5", "Same Title", "Same body text"))
        insert_post(_make_post("post6", "Same Title", "Same body text"))

        result1 = run_dedup()
        result2 = run_dedup()

        assert result1["exact_reposts"] == result2["exact_reposts"]

    def test_empty_db_runs_without_error(self):
        result = run_dedup()
        assert result == {"hashes_updated": 0, "exact_reposts": 0, "near_reposts": 0}

    def test_canonical_post_id_set_on_duplicate(self):
        insert_post(_make_post("earliest", "Duplicate Post", "Same body content"))
        insert_post(_make_post("later", "Duplicate Post", "Same body content"))

        run_dedup()

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT post_id, canonical_post_id FROM posts WHERE dedup_status='exact_repost'"
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        assert row is not None
        assert row[1] is not None  # canonical_post_id is populated
