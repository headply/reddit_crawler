"""Scam detection module for Reddit job posts."""

from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.db import _placeholder, execute_query, get_connection

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT = """You are a scam detector for job postings on Reddit. Given a post,
return JSON: {"is_scam": bool, "reasons": [list of short strings],
"confidence": 0.0-1.0}.

Common scam patterns to flag:
- Pay-to-apply or pay-for-training schemes
- "Equity only" with no salary and no funding signal
- Reshipping/package-forwarding "jobs"
- Crypto/Web3 roles asking for wallet access or seed phrases
- MLM, pyramid, recruitment-of-recruiters language
- Unrealistic comp ($200/hr for entry-level, etc.)
- Vague "remote data entry" with no company name
- WhatsApp/Telegram-only contact, no LinkedIn/website
- Grammar/formatting consistent with scam templates
- Recruiter username < 30 days old with no other activity

Be conservative — only flag when at least 2 signals are present
or one very strong signal. Confidence < 0.6 → set is_scam=false.

Return ONLY the JSON object with no additional text or markdown."""


def _get_client():
    """Return an Anthropic client using ANTHROPIC_API_KEY."""
    import anthropic  # noqa: PLC0415

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


def openai_available() -> bool:
    """Return True if the Anthropic API key is configured."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _classify_scam(post: dict[str, Any]) -> dict[str, Any]:
    """Classify a single post for scam signals."""
    client = _get_client()
    title = post.get("title", "")
    body = (post.get("body") or "")[:700]

    response = client.messages.create(
        model=_MODEL,
        max_tokens=250,
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[
            {"role": "user", "content": f"Title: {title}\n\nBody: {body}"},
        ],
    )

    raw = json.loads(response.content[0].text)
    confidence = float(raw.get("confidence", 0.0))
    is_scam = bool(raw.get("is_scam", False)) and confidence >= 0.6
    reasons = raw.get("reasons") or []

    return {
        "post_id": post["post_id"],
        "is_scam": is_scam,
        "reasons": reasons,
        "confidence": confidence,
    }


def flag_scams(max_workers: int = 10) -> dict[str, int]:
    """Detect scam posts that have not yet been evaluated.

    Returns:
        Dict with scanned and flagged counts.
    """
    if not openai_available():
        logger.warning("ANTHROPIC_API_KEY missing; skipping scam detection.")
        return {"scanned": 0, "flagged": 0}

    rows = execute_query(
        """SELECT p.post_id, p.title, p.body, p.subreddit, p.author, p.created_utc, p.post_url
           FROM posts p
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE jc.is_scam IS NULL""",
        fetch=True,
    )
    posts = [dict(row) for row in rows]
    if not posts:
        return {"scanned": 0, "flagged": 0}

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_classify_scam, post): post["post_id"] for post in posts}
        for future in as_completed(futures):
            post_id = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                logger.error("Scam detection failed for %s: %s", post_id, exc)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        ph = _placeholder()
        flagged = 0
        for result in results:
            is_scam = result["is_scam"]
            reasons = json.dumps(result["reasons"], ensure_ascii=True)
            cursor.execute(
                f"""UPDATE job_classifications
                   SET is_scam = {ph},
                       scam_reasons = {ph}
                   WHERE post_id = {ph}""",
                (is_scam, reasons, result["post_id"]),
            )
            if is_scam:
                flagged += 1
                logger.warning(
                    "Scam flagged: %s | reasons=%s",
                    result["post_id"],
                    ", ".join(result["reasons"]),
                )
        conn.commit()
    finally:
        conn.close()

    return {"scanned": len(results), "flagged": flagged}
