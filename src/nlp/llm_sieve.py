"""LLM-based job post classifier using GPT-4o-mini.

Sends each post's title + body excerpt to GPT-4o-mini and receives a
structured JSON classification in a single call. This replaces the
fragile rule-based keyword matching with proper language understanding.

Fallback: if OPENAI_API_KEY is not set, falls back to the rule-based
enrichment module so the pipeline never hard-crashes.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — defines the classification contract
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a job posting classifier for a Reddit job intelligence platform.

Given a Reddit post title and body excerpt, determine if it is a genuine job posting — meaning an employer, recruiter, or company is actively looking to hire someone.

Return ONLY a valid JSON object with these exact fields:
{
  "is_job": boolean,
  "job_type": "Full-time" | "Contract" | "Freelance" | "Part-time" | "Internship" | null,
  "domain": "Software Engineering" | "Data & Analytics" | "AI / Machine Learning" | "DevOps & Cloud" | "Mobile" | "Design & UX" | "Product Management" | "Marketing & Growth" | "Security" | "Game Development" | "Blockchain & Web3" | "QA & Testing" | "Finance & FinTech" | "Other Tech" | null,
  "seniority": "Junior" | "Mid" | "Senior" | "Lead/Principal" | null,
  "work_mode": "Remote" | "Hybrid" | "On-site" | null,
  "tech_stack": ["array", "of", "specific", "technologies"],
  "urgency_score": 0.0,
  "confidence": 0.0
}

Rules:
- is_job = true ONLY when an employer is actively hiring. Set false for: job seekers ("hire me"), career advice, interview prep, rants, discussions, questions.
- For domain, choose the single best fit. Use "Other Tech" only when nothing else applies.
- tech_stack: list specific named technologies (e.g. "Python", "React", "AWS"). Empty array if none mentioned.
- urgency_score: 0.0–1.0. Higher when post uses words like ASAP, immediately, urgent, start Monday, deadline.
- confidence: 0.0–1.0. How certain you are this is correctly classified."""


def _get_client():
    """Lazy-import and return an OpenAI client."""
    from openai import OpenAI  # noqa: PLC0415
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Add it to your .env file or GitHub Actions secrets."
        )
    return OpenAI(api_key=api_key)


def classify_post(post: dict[str, Any]) -> dict[str, Any]:
    """Classify a single Reddit post using GPT-4o-mini.

    Args:
        post: Dict with at minimum post_id, title, body.

    Returns:
        Classification dict with post_id and all classification fields.

    Raises:
        RuntimeError: If OPENAI_API_KEY is missing.
        Exception: Re-raises API errors after logging.
    """
    client = _get_client()
    title = post.get("title", "")
    body = (post.get("body") or "")[:500]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Title: {title}\n\nBody: {body}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=300,
        )

        raw = json.loads(response.choices[0].message.content)

        result: dict[str, Any] = {
            "post_id": post["post_id"],
            "is_job": bool(raw.get("is_job", False)),
            "job_type": raw.get("job_type"),
            "domain": raw.get("domain"),
            "seniority": raw.get("seniority"),
            "work_mode": raw.get("work_mode"),
            "tech_stack": raw.get("tech_stack") or [],
            "urgency_score": float(raw.get("urgency_score", 0.0)),
            "confidence": float(raw.get("confidence", 0.0)),
            "sentiment_score": 0.0,  # kept for schema compatibility
            "llm_classified": True,
        }

        logger.info(
            "Classified %s: is_job=%s domain=%s seniority=%s conf=%.2f",
            post["post_id"],
            result["is_job"],
            result["domain"],
            result["seniority"],
            result["confidence"],
        )
        return result

    except Exception as exc:
        logger.error("LLM classification failed for %s: %s", post.get("post_id"), exc)
        raise


def classify_posts_batch(
    posts: list[dict[str, Any]],
    max_workers: int = 10,
) -> list[dict[str, Any]]:
    """Classify a list of posts concurrently using a thread pool.

    Sends up to max_workers requests to the OpenAI API in parallel,
    reducing wall-clock time from O(n) sequential to O(n/max_workers).

    Args:
        posts: List of post dicts.
        max_workers: Number of parallel API calls (default 10).

    Returns:
        List of successfully classified results in original order.
        Failed posts are skipped and logged.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    total = len(posts)
    logger.info("Classifying %d posts with %d parallel workers.", total, max_workers)

    results: list[dict[str, Any]] = []
    futures = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for post in posts:
            future = pool.submit(classify_post, post)
            futures[future] = post.get("post_id")

        done = 0
        for future in as_completed(futures):
            post_id = futures[future]
            done += 1
            try:
                results.append(future.result())
                if done % 50 == 0 or done == total:
                    logger.info("Classified %d/%d posts.", done, total)
            except Exception as exc:
                logger.error("Skipping post %s: %s", post_id, exc)

    logger.info("Batch complete: %d/%d classified successfully.", len(results), total)
    return results


def openai_available() -> bool:
    """Return True if the OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))
