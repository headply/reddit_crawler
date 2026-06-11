"""Airflow DAG for the Reddit Job Intelligence pipeline.

Runs twice daily (05:00 and 17:00 UTC). Every task is wrapped so a single
failure does not propagate — the pipeline always completes, with the rule
fallback taking over whenever the LLM is unresponsive.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# Comma-separated list of recipients for failure / SLA-miss alerts.
ALERT_EMAILS = [e.strip() for e in os.getenv("ALERT_EMAIL", "").split(",") if e.strip()]

# Open file handle for faulthandler dumps; kept alive at module scope so the
# timer thread can keep writing to it for the duration of the scrape task.
_FAULT_DUMP_FH = None

def _send_resend_email(subject: str, body: str) -> None:
    """Send an alert via Resend's HTTPS API (port 443).

    We deliberately do NOT use Airflow's SMTP email_on_failure: DigitalOcean
    blocks outbound SMTP ports (25/465/587), so smtplib just times out — which
    both fails to alert AND stalls the failure path for minutes. The Resend
    REST API over HTTPS is never blocked. A hard 15s timeout guarantees the
    alert path itself can never hang the worker.
    """
    import json
    import urllib.request

    api_key = os.getenv("RESEND_API_KEY")
    mail_from = os.getenv("ALERT_EMAIL_FROM")
    if not (api_key and mail_from and ALERT_EMAILS):
        logger.warning("Resend alert skipped: RESEND_API_KEY/ALERT_EMAIL_FROM/ALERT_EMAIL not all set.")
        return

    payload = json.dumps({
        "from": mail_from,
        "to": ALERT_EMAILS,
        "subject": subject,
        "text": body,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.info("Resend alert sent (HTTP %s): %s", resp.status, subject)
    except Exception as exc:  # noqa: BLE001 — alerting must never raise
        logger.error("Resend alert failed to send: %s", exc)


def _alert_failure(context: dict[str, Any]) -> None:
    """on_failure_callback — POST a failure alert via Resend HTTPS."""
    ti = context.get("task_instance")
    dag_id = getattr(ti, "dag_id", "reddit_jobs_pipeline")
    task_id = getattr(ti, "task_id", "?")
    exc = context.get("exception")
    log_url = getattr(ti, "log_url", "")
    _send_resend_email(
        subject=f"[Airflow] FAILED: {dag_id}.{task_id}",
        body=f"Task {task_id} in {dag_id} failed.\n\nException: {exc}\n\nLog: {log_url}",
    )


DEFAULT_ARGS: dict[str, Any] = {
    "owner": "mayowa",
    # Alert on failure via Resend's HTTPS API (NOT SMTP — DO blocks SMTP ports).
    # email_on_failure is left off so smtplib is never invoked.
    "email_on_failure": False,
    "on_failure_callback": _alert_failure,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=35),
}

# How many freshly-scraped posts to classify per DAG run.
# The rule fallback is pure-Python and free, so when the LLM is down we still
# want to drain the entire backlog rather than trickle 300/run (the old cap is
# exactly why ~10k scraped posts left only ~300 visible on the dashboard).
CLASSIFY_BATCH_LIMIT = int(os.getenv("CLASSIFY_BATCH_LIMIT", "5000"))

# How many rule-fallback rows to upgrade with the LLM per DAG run.
RECLASSIFY_BATCH_LIMIT = 300


def _alert_sla_miss(dag, task_list, blocking_task_list, slas, blocking_tis):  # noqa: ANN001
    """SLA-miss callback — fires WHILE a task is still running past its SLA.

    This is the safety net that turns a future hang into a 15-minute alert
    instead of a multi-day silent outage: unlike execution_timeout (which
    relies on a SIGTERM the hung process may ignore), the SLA miss is detected
    by the scheduler independently of the stuck task.
    """
    # `slas` is the list of SlaMiss records (each has .task_id); `task_list`
    # is a pre-formatted string, so we read task ids off `slas`.
    missed = [getattr(s, "task_id", str(s)) for s in (slas or [])]
    logger.error(
        "SLA MISS on reddit_jobs_pipeline — tasks %s exceeded their SLA. "
        "Likely a hang (DB/PRAW). Check the faulthandler dump in the task log.",
        missed or task_list,
    )
    _send_resend_email(
        subject="[Airflow] SLA MISS: reddit_jobs_pipeline",
        body=(
            f"Tasks {missed or task_list} exceeded their SLA and are likely "
            f"hung (DB/PRAW). Check the faulthandler dump in the scrape task log."
        ),
    )


# ---------------------------------------------------------------------------
# Task callables — each returns a dict pushed to XCom; never raises.
# ---------------------------------------------------------------------------
def scrape_reddit_task(**context: Any) -> dict[str, int]:
    # If the scrape is still alive after 20 min (a healthy run is ~3 min), dump
    # every thread's stack so the next hang's frozen frame (e.g. psycopg2
    # connect, prawcore sleep) is captured automatically.
    #
    # faulthandler needs a real file descriptor; Airflow's wrapped sys.stderr
    # has none (io.UnsupportedOperation: fileno), so we point it at an actual
    # file on the mounted logs volume and log the path.
    import faulthandler
    dump_path = f"/opt/airflow/logs/faulthandler_scrape_{os.getpid()}.log"
    try:
        global _FAULT_DUMP_FH
        _FAULT_DUMP_FH = open(dump_path, "w")  # kept open via module ref
        faulthandler.dump_traceback_later(20 * 60, repeat=True, file=_FAULT_DUMP_FH)
        logger.info("faulthandler armed; stack dumps (if any) → %s", dump_path)
    except Exception as exc:  # noqa: BLE001 — diagnostics must never fail the task
        logger.warning("Could not arm faulthandler: %s", exc)
    try:
        from src.scrape.reddit_scraper import scrape_all
        posts = scrape_all()
        count = len(posts)
        logger.info("Scraped %d new posts.", count)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scrape failed: %s", exc)
        count = 0
    finally:
        faulthandler.cancel_dump_traceback_later()
        fh = globals().get("_FAULT_DUMP_FH")
        if fh is not None:
            try:
                fh.close()
            except Exception:  # noqa: BLE001
                pass
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
    sla_miss_callback=_alert_sla_miss,
    tags=["reddit", "jobs"],
) as dag:
    scrape_reddit = PythonOperator(
        task_id="scrape_reddit",
        python_callable=scrape_reddit_task,
        # A healthy scrape finishes in ~3 min. If it runs past 15, the
        # scheduler fires the SLA-miss alert while the task is still stuck.
        sla=timedelta(minutes=15),
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
