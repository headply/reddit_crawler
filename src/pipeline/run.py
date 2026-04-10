"""Pipeline orchestrator for the Reddit Job Intelligence Platform.

Coordinates scraping, LLM classification, and database storage.
Uses GPT-4o-mini as the primary classifier. Falls back to rule-based
enrichment if OPENAI_API_KEY is not set.
"""

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.db import (
    execute_query,
    init_db,
    insert_classification,
    insert_tech_stack,
)
from src.scrape.reddit_scraper import scrape_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_unprocessed_posts() -> list[dict[str, Any]]:
    """Fetch posts that have not yet been classified."""
    rows = execute_query(
        """SELECT p.post_id, p.title, p.body, p.subreddit
           FROM posts p
           LEFT JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE jc.post_id IS NULL""",
        fetch=True,
    )
    return [dict(row) for row in rows]


def enrich_and_store(posts: list[dict[str, Any]]) -> int:
    """Classify posts and store results. Uses LLM sieve when available.

    Args:
        posts: List of unclassified post dicts.

    Returns:
        Number of posts successfully classified and stored.
    """
    from src.nlp.llm_sieve import classify_posts_batch, openai_available

    if not posts:
        return 0

    if openai_available():
        logger.info("OpenAI key detected — using LLM classifier.")
        results = classify_posts_batch(posts)
    else:
        logger.warning(
            "OPENAI_API_KEY not set — falling back to rule-based enrichment."
        )
        from src.nlp.enrichment import enrich_post
        results = []
        for post in posts:
            try:
                results.append(enrich_post(post))
            except Exception as exc:
                logger.error("Rule-based enrichment failed for %s: %s", post.get("post_id"), exc)

    stored = 0
    llm = openai_available()
    for result in results:
        try:
            tech_stack = result.pop("tech_stack", [])
            insert_classification({**result, "llm_classified": llm})
            if tech_stack:
                insert_tech_stack(result["post_id"], tech_stack)
            stored += 1
        except Exception as exc:
            logger.error("Failed to store classification for %s: %s", result.get("post_id"), exc)

    return stored


def run_pipeline(skip_scrape: bool = False) -> dict[str, int]:
    """Execute the full pipeline: scrape, classify, store.

    Args:
        skip_scrape: If True, skip scraping and only classify existing posts.

    Returns:
        Dict with counts: scraped, classified.
    """
    logger.info("=" * 60)
    logger.info("Reddit Job Intelligence Pipeline - Starting")
    logger.info("=" * 60)

    init_db()

    scraped_count = 0
    if not skip_scrape:
        logger.info("Step 1: Scraping Reddit...")
        new_posts = scrape_all()
        scraped_count = len(new_posts)
        logger.info("Scraped %d new posts.", scraped_count)
    else:
        logger.info("Step 1: Skipping scrape.")

    logger.info("Step 2: Classifying unprocessed posts...")
    unprocessed = get_unprocessed_posts()
    logger.info("Found %d unprocessed posts.", len(unprocessed))

    classified_count = enrich_and_store(unprocessed)
    logger.info("Classified %d posts.", classified_count)

    logger.info("=" * 60)
    logger.info(
        "Pipeline complete - scraped: %d, classified: %d",
        scraped_count,
        classified_count,
    )
    logger.info("=" * 60)

    return {"scraped": scraped_count, "classified": classified_count}


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    skip = "--skip-scrape" in sys.argv
    run_pipeline(skip_scrape=skip)
