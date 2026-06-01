"""Airflow DAG for the Reddit Job Intelligence pipeline."""

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
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def scrape_reddit_task(**context: Any) -> dict[str, int]:
    """Scrape new Reddit posts and push counts to XCom."""
    from src.scrape.reddit_scraper import scrape_all

    posts = scrape_all()
    count = len(posts)
    logger.info("Scraped %d new posts.", count)
    context["ti"].xcom_push(key="scraped_count", value=count)
    return {"scraped_count": count}


def dedupe_posts_task(**context: Any) -> dict[str, int]:
    """Run exact and near-duplicate detection."""
    from src.dedupe import run_dedup

    result = run_dedup()
    logger.info("Dedup complete: %s", result)
    for key, value in result.items():
        context["ti"].xcom_push(key=key, value=value)
    return result


def classify_posts_task(**context: Any) -> dict[str, int]:
    """Classify unprocessed posts and store results."""
    from src.pipeline.run import enrich_and_store, get_unprocessed_posts

    posts = get_unprocessed_posts()
    count = enrich_and_store(posts)
    logger.info("Classified %d posts.", count)
    context["ti"].xcom_push(key="classified_count", value=count)
    return {"classified_count": count}


def detect_scams_task(**context: Any) -> dict[str, int]:
    """Flag scams with a focused LLM pass."""
    from src.nlp.scam_detector import flag_scams

    result = flag_scams()
    logger.info("Scam detection complete: %s", result)
    for key, value in result.items():
        context["ti"].xcom_push(key=key, value=value)
    return result


def refresh_views_task(**context: Any) -> dict[str, int]:
    """Refresh analytics materialized views."""
    from src.db import refresh_views

    result = refresh_views()
    logger.info("Materialized views refreshed: %s", result)
    for key, value in result.items():
        context["ti"].xcom_push(key=key, value=value)
    return result


def cleanup_old_raw_task(**context: Any) -> dict[str, int]:
    """Remove raw bodies older than 90 days and mark purge time."""
    from src.db import cleanup_old_raw

    purged = cleanup_old_raw()
    logger.info("Purged %d raw bodies.", purged)
    context["ti"].xcom_push(key="raw_bodies_purged", value=purged)
    return {"raw_bodies_purged": purged}


with DAG(
    dag_id="reddit_jobs_pipeline",
    default_args=DEFAULT_ARGS,
    description="Daily Reddit job intelligence pipeline",
    schedule="0 6 * * *",
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

    scrape_reddit >> dedupe_posts >> classify_posts >> detect_scams >> refresh_materialized_views >> cleanup_old_raw_data
