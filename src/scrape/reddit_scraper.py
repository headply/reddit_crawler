"""Reddit scraper module using PRAW.

Scrapes job-related posts from configured subreddits,
collecting only new posts to avoid duplicates.
"""

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional

import praw
from praw.models import Submission

from src.config import (
    POSTS_PER_GROUP,
    POSTS_PER_SUBREDDIT,
    SUBREDDIT_INCLUDE_KEYWORDS,
    SUBREDDIT_TO_GROUP,
    TARGET_SUBREDDITS,
)
from src.db import get_connection, insert_posts_bulk

logger = logging.getLogger(__name__)

# PRAW (and its underlying requests.Session + rate-limit state) is NOT
# thread-safe. Sharing one client across a ThreadPoolExecutor was a latent
# cause of the pipeline hang: concurrent threads mutating the shared
# rate-limiter could wedge in its throttling sleep. We give each worker
# thread its own client via thread-local storage instead.
_thread_local = threading.local()


def get_thread_reddit_client() -> praw.Reddit:
    """Return a PRAW client unique to the calling thread."""
    client = getattr(_thread_local, "reddit", None)
    if client is None:
        client = create_reddit_client()
        _thread_local.reddit = client
    return client


def create_reddit_client() -> praw.Reddit:
    """Create and return an authenticated Reddit client.

    Returns:
        praw.Reddit: Authenticated Reddit instance.

    Raises:
        ValueError: If required environment variables are missing.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "reddit-job-intel/1.0")

    if not client_id or not client_secret:
        raise ValueError(
            "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables are required. "
            "Create an app at https://www.reddit.com/prefs/apps"
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def extract_post_data(submission: Submission) -> dict[str, Any]:
    """Extract relevant fields from a Reddit submission.

    Args:
        submission: PRAW Submission object.

    Returns:
        Dictionary with extracted post data.
    """
    return {
        "post_id": submission.id,
        "title": submission.title,
        "body": submission.selftext or "",
        "author": str(submission.author) if submission.author else "[deleted]",
        "subreddit": str(submission.subreddit),
        "score": submission.score,
        "num_comments": submission.num_comments,
        "created_utc": datetime.fromtimestamp(
            submission.created_utc, tz=timezone.utc
        ).isoformat(),
        "post_url": f"https://www.reddit.com{submission.permalink}",
    }


def _passes_subreddit_filters(subreddit_name: str, post: dict[str, Any]) -> bool:
    """Apply subreddit-specific include filters when configured."""
    keywords = SUBREDDIT_INCLUDE_KEYWORDS.get(subreddit_name.lower())
    if not keywords:
        return True

    text = f"{post.get('title', '')} {post.get('body', '')}".lower()
    return any(kw in text for kw in keywords)


def get_existing_post_ids(subreddit: str) -> set[str]:
    """Get set of already-scraped post IDs for a subreddit.

    Args:
        subreddit: Name of the subreddit.

    Returns:
        Set of post_id strings already in the database.
    """
    from src.db import _placeholder

    conn = get_connection()
    try:
        cursor = conn.cursor()
        ph = _placeholder()
        cursor.execute(
            f"SELECT post_id FROM posts WHERE subreddit = {ph}", (subreddit,)
        )
        rows = cursor.fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()


def scrape_subreddit(
    reddit: praw.Reddit,
    subreddit_name: str,
    limit: int = POSTS_PER_SUBREDDIT,
) -> list[dict[str, Any]]:
    """Scrape new posts from a single subreddit.

    Args:
        reddit: Authenticated Reddit client.
        subreddit_name: Name of the subreddit to scrape.
        limit: Maximum number of posts to fetch.

    Returns:
        List of newly scraped post data dictionaries.
    """
    existing_ids = get_existing_post_ids(subreddit_name)
    candidates: list[dict[str, Any]] = []

    try:
        subreddit = reddit.subreddit(subreddit_name)
        for submission in subreddit.new(limit=limit):
            if submission.id not in existing_ids:
                post_data = extract_post_data(submission)
                if not _passes_subreddit_filters(subreddit_name, post_data):
                    continue
                candidates.append(post_data)
    except Exception as e:
        logger.error("Error scraping r/%s: %s", subreddit_name, str(e))
        return []

    if not candidates:
        return []

    # One bulk insert per subreddit instead of one connection per post.
    inserted = insert_posts_bulk(candidates)
    logger.info(
        "r/%s: %d candidates, %d newly inserted", subreddit_name, len(candidates), inserted
    )
    return candidates[:inserted] if inserted < len(candidates) else candidates


def scrape_all(
    subreddits: Optional[list[str]] = None,
    limit: int = POSTS_PER_SUBREDDIT,
    max_workers: int = 4,
    overall_timeout: float = 1500.0,
) -> list[dict[str, Any]]:
    """Scrape new posts from all configured subreddits in parallel.

    Args:
        subreddits: Optional list of subreddit names. Defaults to config.
        limit: Maximum posts per subreddit.
        max_workers: Number of subreddits to scrape concurrently.
        overall_timeout: Hard wall-clock ceiling (seconds) for the whole
            fan-out. Acts as an in-process backstop below Airflow's
            execution_timeout so a single stuck subreddit cannot consume the
            entire run budget silently.

    Returns:
        List of all newly scraped post data dictionaries.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed

    target = subreddits or TARGET_SUBREDDITS
    all_posts: list[dict[str, Any]] = []

    def _scrape(sub_name: str) -> list[dict[str, Any]]:
        # Each worker uses its own thread-local PRAW client (not shared).
        reddit = get_thread_reddit_client()
        group = SUBREDDIT_TO_GROUP.get(sub_name)
        per_group_limit = POSTS_PER_GROUP.get(group, limit)
        logger.info("Scraping r/%s ...", sub_name)
        posts = scrape_subreddit(reddit, sub_name, per_group_limit)
        logger.info("Found %d new posts in r/%s", len(posts), sub_name)
        return posts

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_scrape, sub): sub for sub in target}
        try:
            for future in as_completed(futures, timeout=overall_timeout):
                try:
                    all_posts.extend(future.result())
                except Exception as exc:
                    logger.error("Error scraping r/%s: %s", futures[future], exc)
        except FuturesTimeout:
            done = sum(1 for f in futures if f.done())
            logger.error(
                "scrape_all hit overall timeout (%.0fs): %d/%d subreddits finished. "
                "Returning partial results.",
                overall_timeout, done, len(futures),
            )

    logger.info("Total new posts scraped: %d", len(all_posts))
    return all_posts
