"""Airflow DAG for the Reddit Job Intelligence pipeline.

Runs twice daily (05:00 and 17:00 UTC). Every task is wrapped so a single
failure does not propagate — the pipeline always completes, with the rule
fallback taking over whenever the LLM is unresponsive.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

DEFAULT_ARGS: dict[str, Any] = {
    "owner": "mayowa",
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=35),
}

# How many freshly-scraped posts to classify per DAG run.
CLASSIFY_BATCH_LIMIT = 300

# How many rule-fallback rows to upgrade with the LLM per DAG run.
RECLASSIFY_BATCH_LIMIT = 300


# ---------------------------------------------------------------------------
# Task callables — each returns a dict pushed to XCom; never raises.
# ---------------------------------------------------------------------------
def scrape_reddit_task(**context: Any) -> dict[str, int]:
    try:
        from src.scrape.reddit_scraper import scrape_all
        posts = scrape_all()
        count = len(posts)
        logger.info("Scraped %d new posts.", count)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scrape failed: %s", exc)
        count = 0
    context["ti"].xcom_push(key="scraped_count", value=count)
    return {"scraped_count": count}


def dedupe_posts_task(**context: Any) -> dict[str, int]:
    try:
        from src.dedupe import run_dedup
        result = run_dedup()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Dedup failed: %s", exc)
        result = {"unique": 0, "duplicates": 0}
    for key, value in result.items():
        context["ti"].xcom_push(key=key, value=value)
    return result


def classify_posts_task(**context: Any) -> dict[str, int]:
    """Classify unprocessed posts; LLM with rule fallback. Never raises."""
    try:
        from src.pipeline.run import enrich_and_store, get_unprocessed_posts

        posts = get_unprocessed_posts()
        total = len(posts)
        posts = posts[:CLASSIFY_BATCH_LIMIT]
        logger.info(
            "Classifying %d of %d unprocessed posts (batch cap %d).",
            len(posts), total, CLASSIFY_BATCH_LIMIT,
        )
        outcome = enrich_and_store(posts, max_workers=5)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Classification task failed: %s", exc)
        outcome = {"stored": 0, "llm_classified": 0, "rule_fallback": 0, "tripped": True}
        total = 0

    pending = max(0, total - outcome.get("stored", 0))
    for key, value in outcome.items():
        context["ti"].xcom_push(key=key, value=value)
    context["ti"].xcom_push(key="pending_count", value=pending)
    if outcome.get("tripped"):
        logger.warning("LLM breaker tripped during classification — rule fallback used.")
    return outcome


def reclassify_pending_task(**context: Any) -> dict[str, int]:
    """Re-run the LLM on previously rule-classified rows. No-op when LLM down."""
    try:
        from src.pipeline.run import reclassify_pending
        result = reclassify_pending(limit=RECLASSIFY_BATCH_LIMIT, max_workers=5)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reclassify task failed: %s", exc)
        result = {"candidates": 0, "upgraded": 0}
    for key, value in result.items():
        context["ti"].xcom_push(key=key, value=value)
    return result


def detect_scams_task(**context: Any) -> dict[str, int]:
    try:
        from src.nlp.scam_detector import flag_scams
        result = flag_scams()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scam detection failed: %s", exc)
        result = {"scanned": 0, "flagged": 0}
    for key, value in result.items():
        context["ti"].xcom_push(key=key, value=value)
    return result


def refresh_views_task(**context: Any) -> dict[str, int]:
    try:
        from src.db import refresh_views
        result = refresh_views()
    except Exception as exc:  # noqa: BLE001
        logger.exception("View refresh failed: %s", exc)
        result = {"refreshed": 0}
    for key, value in result.items():
        context["ti"].xcom_push(key=key, value=value)
    return result


def cleanup_old_raw_task(**context: Any) -> dict[str, int]:
    try:
        from src.db import cleanup_old_raw
        purged = cleanup_old_raw()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Cleanup failed: %s", exc)
        purged = 0
    context["ti"].xcom_push(key="raw_bodies_purged", value=purged)
    return {"raw_bodies_purged": purged}


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------
with DAG(
    dag_id="reddit_jobs_pipeline",
    default_args=DEFAULT_ARGS,
    description="Reddit job intelligence pipeline (runs twice daily)",
    schedule="0 5,17 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["reddit", "jobs"],
) as dag:
    scrape_reddit = PythonOperator(
        task_id="scrape_reddit",
        python_callable=scrape_reddit_task,
    )

    dedupe_posts = PythonOperator(
        task_id="dedupe_posts",
        python_callable=dedupe_posts_task,
    )

    classify_posts = PythonOperator(
        task_id="classify_posts",
        python_callable=classify_posts_task,
    )

    reclassify_pending = PythonOperator(
        task_id="reclassify_pending",
        python_callable=reclassify_pending_task,
    )

    detect_scams = PythonOperator(
        task_id="detect_scams",
        python_callable=detect_scams_task,
    )

    refresh_materialized_views = PythonOperator(
        task_id="refresh_materialized_views",
        python_callable=refresh_views_task,
    )

    cleanup_old_raw_data = PythonOperator(
        task_id="cleanup_old_raw_data",
        python_callable=cleanup_old_raw_task,
    )

    (
        scrape_reddit
        >> dedupe_posts
        >> classify_posts
        >> reclassify_pending
        >> detect_scams
        >> refresh_materialized_views
        >> cleanup_old_raw_data
    )
