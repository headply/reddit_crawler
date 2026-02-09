"""Reddit scraper module using PRAW.

Scrapes job-related posts from configured subreddits,
collecting only new posts to avoid duplicates.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import praw
from praw.models import Submission

from src.config import POSTS_PER_SUBREDDIT, TARGET_SUBREDDITS
from src.db import get_connection, insert_post

logger = logging.getLogger(__name__)


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


def get_existing_post_ids(subreddit: str) -> set[str]:
    """Get set of already-scraped post IDs for a subreddit.

    Args:
        subreddit: Name of the subreddit.

    Returns:
        Set of post_id strings already in the database.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT post_id FROM posts WHERE subreddit = ?", (subreddit,)
        ).fetchall()
        return {row["post_id"] for row in rows}
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
    new_posts: list[dict[str, Any]] = []

    try:
        subreddit = reddit.subreddit(subreddit_name)
        for submission in subreddit.new(limit=limit):
            if submission.id not in existing_ids:
                post_data = extract_post_data(submission)
                if insert_post(post_data):
                    new_posts.append(post_data)
                    logger.info("Scraped: [%s] %s", subreddit_name, submission.title[:60])
    except Exception as e:
        logger.error("Error scraping r/%s: %s", subreddit_name, str(e))

    return new_posts


def scrape_all(
    subreddits: Optional[list[str]] = None,
    limit: int = POSTS_PER_SUBREDDIT,
) -> list[dict[str, Any]]:
    """Scrape new posts from all configured subreddits.

    Args:
        subreddits: Optional list of subreddit names. Defaults to config.
        limit: Maximum posts per subreddit.

    Returns:
        List of all newly scraped post data dictionaries.
    """
    target = subreddits or TARGET_SUBREDDITS
    reddit = create_reddit_client()
    all_posts: list[dict[str, Any]] = []

    for sub_name in target:
        logger.info("Scraping r/%s ...", sub_name)
        new_posts = scrape_subreddit(reddit, sub_name, limit)
        all_posts.extend(new_posts)
        logger.info("Found %d new posts in r/%s", len(new_posts), sub_name)

    logger.info("Total new posts scraped: %d", len(all_posts))
    return all_posts
