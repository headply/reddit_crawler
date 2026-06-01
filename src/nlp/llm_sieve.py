"""LLM-based job post classifier using Claude Haiku.

Sends each post's title + body excerpt to claude-haiku-4-5 and receives a
structured JSON classification in a single call. This replaces the
fragile rule-based keyword matching with proper language understanding.

Fallback: if ANTHROPIC_API_KEY is not set, falls back to the rule-based
enrichment module so the pipeline never hard-crashes.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fast keyword pre-filter — runs before any API call
# ---------------------------------------------------------------------------
_QUESTION_PREFIXES = (
    "what is",
    "how do i",
    "should i",
    "is it worth",
    "why does",
)
_META_MARKERS = ("[meta]", "[discussion]", "[mod post]")

_MODEL = "claude-haiku-4-5-20251001"


def _quick_reject_category(title: str, body: str) -> str | None:
    """Return a post_category when the post should skip the LLM."""
    title_clean = (title or "").strip().lower()
    total_len = len((title or "") + " " + (body or ""))

    if total_len < 50:
        return "other"

    if title_clean.startswith("?"):
        return "advice_request"

    if any(title_clean.startswith(pfx) for pfx in _QUESTION_PREFIXES):
        return "advice_request"

    if any(marker in title_clean for marker in _META_MARKERS):
        return "discussion"

    return None

# ---------------------------------------------------------------------------
# System prompt — defines the classification contract
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a job posting classifier for a Reddit job intelligence platform.

Given a Reddit post title and body excerpt, return ONLY a valid JSON object with these exact fields:
{
    "post_category": "hiring" | "for_hire" | "gig_freelance" | "cofounder_search" | "discussion" | "advice_request" | "rant" | "meme" | "scam" | "other",
    "job_type": "Full-time" | "Contract" | "Freelance" | "Part-time" | "Internship" | null,
    "domain": "Software Engineering" | "Data & Analytics" | "AI / Machine Learning" | "DevOps & Cloud" | "Mobile" | "Design & UX" | "Product Management" | "Marketing & Growth" | "Security" | "Game Development" | "Blockchain & Web3" | "QA & Testing" | "Finance & FinTech" | "Other Tech" | null,
    "seniority": "Intern" | "Junior" | "Mid" | "Senior" | "Staff" | "Principal" | "Lead/Manager" | "Director+" | null,
    "work_mode": "Remote" | "Hybrid" | "On-site" | null,
    "industry_vertical": "fintech" | "healthtech" | "edtech" | "ecommerce" | "gaming" | "crypto/web3" | "ai/ml-tooling" | "devtools" | "saas" | "agency-services" | "marketplace" | "social" | "content-media" | "climate" | "other" | null,
    "company_stage": "bootstrapped/indie" | "pre-seed" | "seed" | "series-a" | "series-b-plus" | "public" | "agency" | "enterprise" | "unknown" | null,
    "compensation_min": integer | null,
    "compensation_max": integer | null,
    "compensation_currency": "USD" | "EUR" | "GBP" | "NGN" | "CAD" | "AUD" | "INR" | "other" | null,
    "compensation_period": "hourly" | "monthly" | "annual" | "project" | null,
    "equity_mentioned": boolean,
    "tech_stack": ["array", "of", "specific", "technologies"],
    "urgency_score": 0.0,
    "confidence": 0.0
}

Rules:
- If the post is asking for advice, opinions, or discussing the job market in general — even if it mentions hiring or job titles — return post_category "discussion" or "advice_request". Do not classify it as hiring or for_hire.
- Use "scam" only for posts that read like scams (obvious pay-to-apply, WhatsApp-only, reshipping, etc.).
- tech_stack: list specific named technologies (e.g. "Python", "React", "AWS"). Empty array if none mentioned.
- urgency_score: 0.0–1.0. Higher when post uses words like ASAP, immediately, urgent, start Monday, deadline.
- confidence: 0.0–1.0. How certain you are this is correctly classified.
- Return ONLY the JSON object with no additional text, markdown, or explanation.

Examples:

Input:
Title: [Hiring] Senior Backend Engineer (Python) - Remote - $150k-$180k
Body: Acme Analytics (Series A) is hiring a senior backend engineer. Stack: Python, Postgres, AWS. Equity available.
Output:
{"post_category":"hiring","job_type":"Full-time","domain":"Software Engineering","seniority":"Senior","work_mode":"Remote","industry_vertical":"saas","company_stage":"series-a","compensation_min":150000,"compensation_max":180000,"compensation_currency":"USD","compensation_period":"annual","equity_mentioned":true,"tech_stack":["Python","Postgres","AWS"],"urgency_score":0.2,"confidence":0.86}

Input:
Title: [For Hire] Freelance Product Designer - UI/UX
Body: Solo designer available for freelance gigs. Figma, mobile apps, dashboards.
Output:
{"post_category":"for_hire","job_type":"Freelance","domain":"Design & UX","seniority":null,"work_mode":null,"industry_vertical":null,"company_stage":"bootstrapped/indie","compensation_min":null,"compensation_max":null,"compensation_currency":null,"compensation_period":"project","equity_mentioned":false,"tech_stack":["Figma"],"urgency_score":0.1,"confidence":0.74}

Input:
Title: Should I learn Go or Rust for backend roles?
Body: Looking for advice on which language will help me get a job.
Output:
{"post_category":"advice_request","job_type":null,"domain":null,"seniority":null,"work_mode":null,"industry_vertical":null,"company_stage":null,"compensation_min":null,"compensation_max":null,"compensation_currency":null,"compensation_period":null,"equity_mentioned":false,"tech_stack":["Go","Rust"],"urgency_score":0.0,"confidence":0.9}

Input:
Title: Remote Data Entry - $200/hr - Contact via WhatsApp only
Body: No experience needed. Training available after a small fee. Message +234...
Output:
{"post_category":"scam","job_type":"Contract","domain":null,"seniority":null,"work_mode":"Remote","industry_vertical":"other","company_stage":"unknown","compensation_min":200,"compensation_max":200,"compensation_currency":"USD","compensation_period":"hourly","equity_mentioned":false,"tech_stack":[],"urgency_score":0.4,"confidence":0.88}"""


def _get_client():
    """Lazy-import and return an Anthropic client."""
    import anthropic  # noqa: PLC0415
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Add it to your .env file or environment."
        )
    return anthropic.Anthropic(api_key=api_key)


def classify_post(post: dict[str, Any]) -> dict[str, Any]:
    """Classify a single Reddit post using Claude Haiku.

    Args:
        post: Dict with at minimum post_id, title, body.

    Returns:
        Classification dict with post_id and all classification fields.

    Raises:
        RuntimeError: If ANTHROPIC_API_KEY is missing.
        Exception: Re-raises API errors after logging.
    """
    client = _get_client()
    title = post.get("title", "")
    body = (post.get("body") or "")[:500]

    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=300,
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

        def _to_int(value: Any) -> int | None:
            try:
                return int(float(value)) if value is not None else None
            except (TypeError, ValueError):
                return None

        post_category = raw.get("post_category")
        is_job = post_category in {"hiring", "for_hire", "gig_freelance"}

        result: dict[str, Any] = {
            "post_id": post["post_id"],
            "post_category": post_category,
            "is_job": is_job,
            "job_type": raw.get("job_type"),
            "domain": raw.get("domain"),
            "seniority": raw.get("seniority"),
            "work_mode": raw.get("work_mode"),
            "industry_vertical": raw.get("industry_vertical"),
            "company_stage": raw.get("company_stage"),
            "compensation_min": _to_int(raw.get("compensation_min")),
            "compensation_max": _to_int(raw.get("compensation_max")),
            "compensation_currency": raw.get("compensation_currency"),
            "compensation_period": raw.get("compensation_period"),
            "equity_mentioned": bool(raw.get("equity_mentioned", False)),
            "tech_stack": raw.get("tech_stack") or [],
            "urgency_score": float(raw.get("urgency_score", 0.0)),
            "confidence": float(raw.get("confidence", 0.0)),
            "sentiment_score": 0.0,  # kept for schema compatibility
            "llm_classified": True,
        }

        logger.info(
            "Classified %s: category=%s domain=%s seniority=%s conf=%.2f",
            post["post_id"],
            result["post_category"],
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
    max_workers: int = 20,
) -> list[dict[str, Any]]:
    """Classify a list of posts concurrently using a thread pool.

    Applies a fast keyword pre-filter first to skip obvious non-jobs
    without making any API call, then classifies the remainder in parallel.

    Args:
        posts: List of post dicts.
        max_workers: Number of parallel API calls (default 20).

    Returns:
        List of successfully classified results (jobs and non-jobs).
        Failed posts are skipped and logged.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Pre-filter: mark obvious non-jobs without calling the API
    to_classify, pre_rejected = [], []
    for post in posts:
        category = _quick_reject_category(
            post.get("title", ""),
            post.get("body", "") or "",
        )
        if category:
            pre_rejected.append({
                "post_id": post["post_id"],
                "post_category": category,
                "is_job": False,
                "job_type": None,
                "domain": None,
                "seniority": None,
                "work_mode": None,
                "industry_vertical": None,
                "company_stage": None,
                "compensation_min": None,
                "compensation_max": None,
                "compensation_currency": None,
                "compensation_period": None,
                "equity_mentioned": False,
                "tech_stack": [],
                "urgency_score": 0.0,
                "confidence": 1.0,
                "sentiment_score": 0.0,
                "llm_classified": False,
            })
        else:
            to_classify.append(post)

    logger.info(
        "Pre-filter: %d skipped, %d sent to LLM (of %d total).",
        len(pre_rejected), len(to_classify), len(posts),
    )

    results: list[dict[str, Any]] = list(pre_rejected)

    if not to_classify:
        return results

    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for post in to_classify:
            future = pool.submit(classify_post, post)
            futures[future] = post.get("post_id")

        done = 0
        for future in as_completed(futures):
            post_id = futures[future]
            done += 1
            try:
                results.append(future.result())
                if done % 50 == 0 or done == len(to_classify):
                    logger.info("LLM classified %d/%d.", done, len(to_classify))
            except Exception as exc:
                logger.error("Skipping post %s: %s", post_id, exc)

    logger.info("Batch complete: %d/%d processed.", len(results), len(posts))
    return results


def openai_available() -> bool:
    """Return True if the Anthropic API key is configured."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))
