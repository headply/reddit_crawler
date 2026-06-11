"""Pipeline orchestrator for the Reddit Job Intelligence Platform.

Coordinates scraping, classification (LLM with high-precision rule
fallback), scam detection, view refresh, and raw cleanup.

The classification path is now resilient: a per-run circuit breaker
(``LLMCircuitBreaker``) short-circuits to ``src.nlp.enrichment.enrich_post``
once the LLM is clearly unresponsive. No step can crash the whole run —
every helper is wrapped in try/except and returns a sensible default.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.db import (
    _placeholder,
    execute_query,
    init_db,
    persist_classifications_bulk,
)
from src.nlp.circuit_breaker import LLMCircuitBreaker
from src.scrape.reddit_scraper import scrape_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def get_unprocessed_posts() -> list[dict[str, Any]]:
    """Posts that have no classification row yet."""
    rows = execute_query(
        """SELECT p.post_id, p.title, p.body, p.subreddit
           FROM posts p
           LEFT JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE jc.post_id IS NULL""",
        fetch=True,
    )
    return [dict(row) for row in rows]


def get_rule_classified_for_upgrade(limit: int) -> list[dict[str, Any]]:
    """Rows previously written by the rule fallback that are worth retrying
    with the LLM.

    Skips pre-rejected categories so we don't burn tokens on advice/rant.
    """
    ph = _placeholder()
    rows = execute_query(
        f"""SELECT p.post_id, p.title, p.body, p.subreddit
           FROM posts p
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE jc.llm_classified = FALSE
             AND COALESCE(jc.post_category, '') NOT IN
                 ('other','discussion','advice_request','rant','meme')
           ORDER BY p.created_utc DESC
           LIMIT {ph}""",
        (limit,),
        fetch=True,
    )
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------
def _prepare_for_persist(result: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Normalize a classification and split off its tech stack.

    Returns ``(classification_without_tech, tech_stack_list)``. Mirrors the
    normalization the old per-row ``_persist`` did, but without any DB writes
    so the whole batch can be persisted over a single connection.
    """
    post_category = result.get("post_category")
    if post_category is None:
        post_category = "hiring" if result.get("is_job") else "other"
    result["post_category"] = post_category
    result["is_job"] = post_category in {"hiring", "for_hire", "gig_freelance"}
    tech_stack = result.pop("tech_stack", []) or []
    return result, tech_stack


def _persist_all(results: list[dict[str, Any]]) -> int:
    """Persist a whole batch of classifications over ONE connection.

    Replaces the previous ``sum(_persist(r) for r in results)`` loop, which
    opened ~2 connections per post and overwhelmed the Supabase pooler on
    large (e.g. 10k) rule-fallback batches. Returns rows stored (0 on failure).
    """
    if not results:
        return 0

    tech_by_post: dict[str, list[str]] = {}
    prepared: list[dict[str, Any]] = []
    for r in results:
        classification, tech = _prepare_for_persist(r)
        prepared.append(classification)
        if tech:
            tech_by_post[classification["post_id"]] = tech

    try:
        return persist_classifications_bulk(prepared, tech_by_post)
    except Exception as exc:  # noqa: BLE001
        logger.error("Bulk persist of %d classifications failed: %s", len(prepared), exc)
        return 0


# ---------------------------------------------------------------------------
# Classification entry points used by the DAG
# ---------------------------------------------------------------------------
def enrich_and_store(
    posts: list[dict[str, Any]],
    max_workers: int = 10,
    breaker: LLMCircuitBreaker | None = None,
) -> dict[str, int]:
    """Classify ``posts`` and persist. Never raises.

    Returns counts ``{stored, llm_classified, rule_fallback, tripped}``.
    """
    if not posts:
        return {"stored": 0, "llm_classified": 0, "rule_fallback": 0, "tripped": False}

    from src.nlp.llm_sieve import classify_posts_batch

    breaker = breaker or LLMCircuitBreaker(threshold=5, name="classify")
    try:
        results = classify_posts_batch(posts, max_workers=max_workers, breaker=breaker)
    except Exception as exc:  # noqa: BLE001
        # classify_posts_batch is documented to never raise, but be defensive.
        logger.exception("Unexpected error in classify_posts_batch: %s", exc)
        breaker.force_trip(f"unexpected: {exc}")
        from src.nlp.enrichment import enrich_post as rule_enrich
        results = []
        for post in posts:
            try:
                r = rule_enrich(post)
                r["llm_classified"] = False
                results.append(r)
            except Exception as inner:  # noqa: BLE001
                logger.error("Rule fallback failed for %s: %s", post.get("post_id"), inner)

    llm_n = sum(1 for r in results if r.get("llm_classified"))
    stored = _persist_all(results)
    rule_n = max(0, stored - llm_n)
    logger.info(
        "enrich_and_store: stored=%d llm=%d rule=%d (%s)",
        stored, llm_n, rule_n, breaker.status_message(),
    )
    return {
        "stored": stored,
        "llm_classified": llm_n,
        "rule_fallback": rule_n,
        "tripped": breaker.is_tripped(),
    }


def reclassify_pending(
    limit: int,
    max_workers: int = 10,
) -> dict[str, int]:
    """Re-run the LLM on previously rule-classified rows.

    No-op (and returns zeros) when the LLM is unavailable or the breaker
    trips on entry. Safe to call every DAG run.
    """
    from src.nlp.llm_sieve import openai_available

    if not openai_available():
        logger.info("reclassify_pending: LLM unavailable; no-op.")
        return {"candidates": 0, "upgraded": 0}

    try:
        candidates = get_rule_classified_for_upgrade(limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("reclassify_pending: failed to query candidates: %s", exc)
        return {"candidates": 0, "upgraded": 0, "error": str(exc)}

    if not candidates:
        return {"candidates": 0, "upgraded": 0}

    logger.info("reclassify_pending: upgrading %d rows with LLM", len(candidates))
    breaker = LLMCircuitBreaker(threshold=5, name="reclassify")
    result = enrich_and_store(candidates, max_workers=max_workers, breaker=breaker)
    return {
        "candidates": len(candidates),
        "upgraded": result["llm_classified"],
        "tripped": result["tripped"],
    }


# ---------------------------------------------------------------------------
# Standalone runner (kept for manual / cron use; Airflow uses tasks below)
# ---------------------------------------------------------------------------
def run_pipeline(skip_scrape: bool = False) -> dict[str, int]:
    logger.info("=" * 60)
    logger.info("Reddit Job Intelligence Pipeline - Starting")
    logger.info("=" * 60)

    init_db()

    scraped_count = 0
    if not skip_scrape:
        logger.info("Step 1: Scraping Reddit...")
        try:
            new_posts = scrape_all()
            scraped_count = len(new_posts)
        except Exception as exc:  # noqa: BLE001
            logger.error("Scrape step failed: %s", exc)
        logger.info("Scraped %d new posts.", scraped_count)

    logger.info("Step 2: Running deduplication...")
    try:
        from src.dedupe import run_dedup
        run_dedup()
    except Exception as exc:  # noqa: BLE001
        logger.error("Deduplication failed: %s", exc)

    logger.info("Step 3: Classifying unprocessed posts...")
    try:
        unprocessed = get_unprocessed_posts()
        logger.info("Found %d unprocessed posts.", len(unprocessed))
        enrich_and_store(unprocessed)
    except Exception as exc:  # noqa: BLE001
        logger.error("Classification step failed: %s", exc)

    logger.info("Step 3b: Reclassifying rule-fallback rows with LLM...")
    try:
        reclassify_pending(limit=300)
    except Exception as exc:  # noqa: BLE001
        logger.error("Reclassify step failed: %s", exc)

    logger.info("Step 4: Scam detection...")
    try:
        from src.nlp.scam_detector import flag_scams
        flag_scams()
    except Exception as exc:  # noqa: BLE001
        logger.error("Scam detection failed: %s", exc)

    logger.info("Step 5: Refreshing analytics views...")
    try:
        from src.db import refresh_views
        refresh_views()
    except Exception as exc:  # noqa: BLE001
        logger.error("View refresh failed: %s", exc)

    logger.info("Step 6: Cleaning up old raw data...")
    try:
        from src.db import cleanup_old_raw
        cleanup_old_raw()
    except Exception as exc:  # noqa: BLE001
        logger.error("Raw cleanup failed: %s", exc)

    logger.info("=" * 60)
    logger.info("Pipeline complete - scraped: %d", scraped_count)
    logger.info("=" * 60)

    return {"scraped": scraped_count}


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    skip = "--skip-scrape" in sys.argv
    run_pipeline(skip_scrape=skip)
