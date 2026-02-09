"""Pipeline orchestrator for the Reddit Job Intelligence Platform.

Coordinates scraping, NLP enrichment, and database storage.
Can be run as a standalone script or imported.
"""

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.db import (
    init_db,
    insert_classification,
    insert_tech_stack,
    execute_query,
)
from src.nlp.enrichment import enrich_post
from src.scrape.reddit_scraper import scrape_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_unprocessed_posts() -> list[dict[str, Any]]:
    """Fetch posts that have not yet been classified.

    Returns:
        List of post dictionaries awaiting enrichment.
    """
    rows = execute_query(
        """SELECT p.post_id, p.title, p.body, p.subreddit
           FROM posts p
           LEFT JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE jc.post_id IS NULL""",
        fetch=True,
    )
    return [dict(row) for row in rows]


def enrich_and_store(posts: list[dict[str, Any]]) -> int:
    """Enrich posts with NLP and store results in the database.

    Args:
        posts: List of post dictionaries to enrich.

    Returns:
        Number of posts successfully enriched.
    """
    enriched_count = 0
    for post in posts:
        try:
            result = enrich_post(post)
            tech_stack = result.pop("tech_stack", [])

            insert_classification(result)
            if tech_stack:
                insert_tech_stack(result["post_id"], tech_stack)

            enriched_count += 1
        except Exception as e:
            logger.error("Error enriching post %s: %s", post.get("post_id"), str(e))

    return enriched_count


def run_pipeline(skip_scrape: bool = False) -> dict[str, int]:
    """Execute the full pipeline: scrape, enrich, store.

    Args:
        skip_scrape: If True, skip scraping and only enrich existing posts.

    Returns:
        Dictionary with counts of scraped and enriched posts.
    """
    logger.info("=" * 60)
    logger.info("Reddit Job Intelligence Pipeline - Starting")
    logger.info("=" * 60)

    # Initialize database
    init_db()
    logger.info("Database initialized.")

    # Step 1: Scrape
    scraped_count = 0
    if not skip_scrape:
        logger.info("Step 1: Scraping Reddit...")
        new_posts = scrape_all()
        scraped_count = len(new_posts)
        logger.info("Scraped %d new posts.", scraped_count)
    else:
        logger.info("Step 1: Skipping scrape (--skip-scrape flag).")

    # Step 2: Enrich unprocessed posts
    logger.info("Step 2: Enriching posts with NLP...")
    unprocessed = get_unprocessed_posts()
    logger.info("Found %d unprocessed posts.", len(unprocessed))

    enriched_count = enrich_and_store(unprocessed)
    logger.info("Enriched %d posts.", enriched_count)

    # Summary
    logger.info("=" * 60)
    logger.info("Pipeline complete: %d scraped, %d enriched", scraped_count, enriched_count)
    logger.info("=" * 60)

    return {"scraped": scraped_count, "enriched": enriched_count}


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    skip = "--skip-scrape" in sys.argv
    run_pipeline(skip_scrape=skip)
