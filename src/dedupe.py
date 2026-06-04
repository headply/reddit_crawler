"""Deduplication utilities for Reddit job posts."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from src.db import _is_postgres, _placeholder, get_connection

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://\S+")
_MD_RE = re.compile(r"[\[\]\(\)\*\_\~\`>#\-]")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    """Normalize text by lowercasing, stripping URLs, and collapsing whitespace."""
    text = text.lower()
    text = _URL_RE.sub(" ", text)
    text = _MD_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _title_tokens(title: str) -> str:
    """Return lowercase alphanumeric title tokens as a space-separated string."""
    tokens = _TOKEN_RE.findall(title.lower())
    return " ".join(tokens)


def _content_hash(title: str, body: str) -> str:
    """Return a SHA256 hash of normalized title + body."""
    normalized = f"{_normalize(title)} {_normalize(body)}".strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _update_missing_hashes(conn) -> int:
    """Compute hashes and title tokens for posts missing them."""
    cursor = conn.cursor()
    ph = _placeholder()
    cursor.execute(
        """SELECT post_id, title, body
           FROM posts
           WHERE content_hash IS NULL
              OR title_tokens IS NULL"""
    )
    rows = cursor.fetchall()
    updates: list[tuple[str, str, str]] = []
    for row in rows:
        post_id = row[0]
        title = row[1] or ""
        body = row[2] or ""
        updates.append((
            _content_hash(title, body),
            _title_tokens(title),
            post_id,
        ))

    if not updates:
        return 0

    cursor.executemany(
        f"""UPDATE posts
           SET content_hash = {ph},
               title_tokens = {ph}
           WHERE post_id = {ph}""",
        updates,
    )
    conn.commit()
    return len(updates)


def _parse_created(value: Any) -> datetime:
    """Parse created_utc into a timezone-aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.now(tz=timezone.utc)


def _exact_dedupe(conn) -> int:
    """Mark exact reposts by content_hash."""
    cursor = conn.cursor()
    ph = _placeholder()
    cursor.execute(
        """SELECT post_id, content_hash, created_utc
           FROM posts
           WHERE content_hash IS NOT NULL
           ORDER BY content_hash, created_utc, post_id"""
    )
    rows = cursor.fetchall()

    exact_updates: list[tuple[str, str]] = []
    unique_updates: list[str] = []
    current_hash = None
    canonical_id = None

    for post_id, content_hash, created_utc in rows:
        if content_hash != current_hash:
            current_hash = content_hash
            canonical_id = post_id
            unique_updates.append(post_id)
            continue

        exact_updates.append((canonical_id, post_id))

    for post_id in unique_updates:
        cursor.execute(
            f"""UPDATE posts
               SET dedup_status = 'unique',
                   canonical_post_id = NULL
               WHERE post_id = {ph}""",
            (post_id,),
        )

    for canonical_id, dup_id in exact_updates:
        cursor.execute(
            f"""UPDATE posts
               SET dedup_status = 'exact_repost',
                   canonical_post_id = {ph}
               WHERE post_id = {ph}""",
            (canonical_id, dup_id),
        )

    conn.commit()
    return len(exact_updates)


def _jaccard(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Compute Jaccard similarity between two token lists."""
    set_a, set_b = set(tokens_a), set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _near_dedupe_sql(conn) -> list[tuple[str, str]]:
    """Fetch near-duplicate pairs using pg_trgm similarity.

    Strategy that scales to 10k+ recent posts:
      1. Build a temp table with only the candidate rows (last 7 days,
         unique, title_tokens long enough to be meaningful). Bucket by
         subreddit so we only compare within-subreddit — cross-subreddit
         dupes are vanishingly rare and the full N² self-join across
         everything blows past the Postgres statement timeout.
      2. Use ``set_limit`` + ``%`` trigram operator so the GIN index on
         ``title_tokens`` is used; raw ``similarity(...) >= 0.85`` does
         NOT use the index.
      3. Skip subreddits with > 2000 recent candidates as a safety valve
         (those are noise communities where exact-hash already caught the
         real reposts).
    """
    cursor = conn.cursor()

    # Lower the similarity threshold so % uses the GIN index efficiently.
    cursor.execute("SELECT set_limit(0.85)")

    cursor.execute("""
        CREATE TEMP TABLE IF NOT EXISTS _dedup_candidates (
            post_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title_tokens TEXT NOT NULL,
            tlen INT NOT NULL
        ) ON COMMIT DROP
    """)
    cursor.execute("TRUNCATE _dedup_candidates")
    cursor.execute("""
        INSERT INTO _dedup_candidates (post_id, subreddit, title_tokens, tlen)
        SELECT post_id, subreddit, title_tokens, length(title_tokens)
        FROM posts
        WHERE created_utc >= NOW() - INTERVAL '7 days'
          AND COALESCE(dedup_status, 'unique') = 'unique'
          AND title_tokens IS NOT NULL
          AND length(title_tokens) >= 12
    """)
    cursor.execute("CREATE INDEX ON _dedup_candidates (subreddit)")
    cursor.execute(
        "CREATE INDEX ON _dedup_candidates USING gin (title_tokens gin_trgm_ops)"
    )

    # Drop subreddits whose candidate count would blow up the self-join.
    cursor.execute("""
        DELETE FROM _dedup_candidates c
         USING (
            SELECT subreddit FROM _dedup_candidates
            GROUP BY subreddit HAVING COUNT(*) > 2000
         ) noisy
        WHERE c.subreddit = noisy.subreddit
    """)

    cursor.execute("""
        SELECT p1.post_id, p2.post_id
        FROM _dedup_candidates p1
        JOIN _dedup_candidates p2
          ON p1.subreddit = p2.subreddit
         AND p1.post_id  <  p2.post_id
         AND p1.title_tokens % p2.title_tokens
         AND abs(p1.tlen - p2.tlen) <= 0.3 * greatest(p1.tlen, p2.tlen)
        LIMIT 50000
    """)
    return cursor.fetchall()


def _near_dedupe_python(conn) -> list[tuple[str, str]]:
    """Fetch near-duplicate pairs using Jaccard similarity in Python."""
    cursor = conn.cursor()
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)
    cursor.execute(
        """SELECT post_id, title_tokens, created_utc
           FROM posts
           WHERE COALESCE(dedup_status, 'unique') = 'unique'"""
    )
    rows = cursor.fetchall()

    posts: list[tuple[str, list[str], datetime]] = []
    for post_id, title_tokens, created_utc in rows:
        created = _parse_created(created_utc)
        if created < cutoff:
            continue
        tokens = (title_tokens or "").split()
        posts.append((post_id, tokens, created))

    pairs: list[tuple[str, str]] = []
    for i in range(len(posts)):
        for j in range(i + 1, len(posts)):
            post_a, tokens_a, _ = posts[i]
            post_b, tokens_b, _ = posts[j]
            if not tokens_a or not tokens_b:
                continue
            len_a, len_b = len(tokens_a), len(tokens_b)
            if abs(len_a - len_b) > 0.3 * max(len_a, len_b):
                continue
            if _jaccard(tokens_a, tokens_b) >= 0.85:
                pairs.append((post_a, post_b))

    return pairs


def _build_clusters(pairs: list[tuple[str, str]]) -> list[set[str]]:
    """Build clusters of connected post IDs from pair edges."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in pairs:
        union(a, b)

    clusters: dict[str, set[str]] = {}
    for node in list(parent.keys()):
        root = find(node)
        clusters.setdefault(root, set()).add(node)

    return [members for members in clusters.values() if len(members) > 1]


def _fetch_created_map(conn, post_ids: set[str]) -> dict[str, datetime]:
    """Fetch created_utc for a set of posts."""
    cursor = conn.cursor()
    ph = _placeholder()
    placeholders = ",".join([ph] * len(post_ids))
    cursor.execute(
        f"SELECT post_id, created_utc FROM posts WHERE post_id IN ({placeholders})",
        tuple(post_ids),
    )
    rows = cursor.fetchall()
    return {row[0]: _parse_created(row[1]) for row in rows}


def _apply_near_updates(conn, clusters: list[set[str]]) -> int:
    """Mark near duplicates in each cluster."""
    if not clusters:
        return 0

    all_ids = {pid for cluster in clusters for pid in cluster}
    created_map = _fetch_created_map(conn, all_ids)
    cursor = conn.cursor()
    ph = _placeholder()

    updates: list[tuple[str, str]] = []
    for cluster in clusters:
        canonical = sorted(
            cluster,
            key=lambda pid: (created_map.get(pid, datetime.now(tz=timezone.utc)), pid),
        )[0]
        for pid in cluster:
            if pid == canonical:
                cursor.execute(
                    f"""UPDATE posts
                       SET dedup_status = 'unique',
                           canonical_post_id = NULL
                       WHERE post_id = {ph}""",
                    (pid,),
                )
            else:
                updates.append((canonical, pid))

    for canonical_id, dup_id in updates:
        cursor.execute(
            f"""UPDATE posts
               SET dedup_status = 'near_repost',
                   canonical_post_id = {ph}
               WHERE post_id = {ph}""",
            (canonical_id, dup_id),
        )

    conn.commit()
    return len(updates)


def run_dedup() -> dict[str, int]:
    """Run exact and near-duplicate detection.

    Returns:
        Dict with counts for hash updates and dedup flags.
    """
    conn = get_connection()
    try:
        updated = _update_missing_hashes(conn)
        exact = _exact_dedupe(conn)

        if _is_postgres():
            pairs = _near_dedupe_sql(conn)
        else:
            pairs = _near_dedupe_python(conn)

        clusters = _build_clusters(pairs)
        near = _apply_near_updates(conn, clusters)

        logger.info(
            "Dedup summary: hashes=%d, exact_reposts=%d, near_reposts=%d",
            updated,
            exact,
            near,
        )
        return {
            "hashes_updated": updated,
            "exact_reposts": exact,
            "near_reposts": near,
        }
    finally:
        conn.close()
