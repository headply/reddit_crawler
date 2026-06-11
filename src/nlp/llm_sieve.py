"""LLM-based job post classifier using Claude Haiku.

Sends each post's title + body excerpt to claude-haiku-4-5 and receives a
structured JSON classification in a single call.

Resilience design:

* Each LLM call is retried up to 4 times with exponential backoff +
  jitter on transient errors (rate limits, timeouts, connection errors).
* A per-batch ``LLMCircuitBreaker`` counts post-retry failures. After
  ``threshold`` consecutive failures, the breaker trips and the remainder
  of the batch is routed through ``src.nlp.enrichment.enrich_post`` — the
  pipeline NEVER fails because of an LLM issue.
* If ``ANTHROPIC_API_KEY`` is missing the breaker is force-tripped on
  entry, and every post is routed straight through the rule fallback.
* ``classify_posts_batch`` never raises. Callers receive a list of
  classifications matching the input length minus any post whose
  pre-filter or rule fallback emitted nothing (which never happens with
  the current implementation).
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Any

from src.nlp.circuit_breaker import LLMCircuitBreaker
from src.nlp.enrichment import enrich_post as rule_enrich_post

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
# System prompt
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
- Return ONLY the JSON object with no additional text, markdown, or explanation."""


# ---------------------------------------------------------------------------
# Client + retry helpers
# ---------------------------------------------------------------------------
def _get_client():
    import anthropic  # noqa: PLC0415

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient Anthropic SDK errors worth retrying."""
    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        return False
    retryable = (
        anthropic.RateLimitError,
        anthropic.APITimeoutError,
        anthropic.APIConnectionError,
        anthropic.InternalServerError,
    )
    if isinstance(exc, retryable):
        return True
    # Some HTTP 5xx surface as generic APIError — retry those too.
    api_error = getattr(anthropic, "APIStatusError", None)
    if api_error and isinstance(exc, api_error):
        status = getattr(exc, "status_code", None)
        return status is not None and status >= 500
    return False


def _is_fatal_llm_error(exc: BaseException) -> bool:
    """Return True for errors that mean the LLM is unusable for the whole run.

    A 401 (bad key), 403 (permission), or a 400 billing/credit error will not
    fix itself mid-run, so there is no point making the same doomed call for
    every remaining post. These trip the breaker immediately rather than
    waiting for ``threshold`` consecutive failures. A 429 (rate limit) is NOT
    fatal — it is transient and handled by the retry path.
    """
    try:
        import anthropic  # noqa: PLC0415
    except ImportError:
        return False

    fatal_types = tuple(
        t for t in (
            getattr(anthropic, "AuthenticationError", None),   # 401
            getattr(anthropic, "PermissionDeniedError", None),  # 403
        ) if t is not None
    )
    if fatal_types and isinstance(exc, fatal_types):
        return True

    # Any other 4xx except 429 (rate limit) is a non-recoverable client error
    # for this run — most importantly the 400 returned when credit is exhausted.
    api_error = getattr(anthropic, "APIStatusError", None)
    if api_error and isinstance(exc, api_error):
        status = getattr(exc, "status_code", None)
        if status is not None and 400 <= status < 500 and status != 429:
            return True
    return False


def _retrying_call(fn, *, max_attempts: int = 4, base: float = 1.5, cap: float = 30.0):
    """Run ``fn()`` with exponential backoff + jitter on transient errors."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            attempt += 1
            if attempt >= max_attempts or not _is_retryable(exc):
                raise
            delay = min(cap, base * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.25)
            logger.info(
                "LLM call retry %d/%d after %.1fs (%s)",
                attempt, max_attempts - 1, delay, exc.__class__.__name__,
            )
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Classification primitives
# ---------------------------------------------------------------------------
def _coerce_int(value: Any) -> int | None:
    try:
        return int(float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _llm_classify_one(client, post: dict[str, Any]) -> dict[str, Any]:
    """Single LLM call with retry. Raises on unrecoverable errors."""
    title = post.get("title", "")
    body = (post.get("body") or "")[:500]

    def _call():
        return client.messages.create(
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

    response = _retrying_call(_call)
    raw = json.loads(response.content[0].text)

    post_category = raw.get("post_category")
    is_job = post_category in {"hiring", "for_hire", "gig_freelance"}

    return {
        "post_id": post["post_id"],
        "post_category": post_category,
        "is_job": is_job,
        "job_type": raw.get("job_type"),
        "domain": raw.get("domain"),
        "seniority": raw.get("seniority"),
        "work_mode": raw.get("work_mode"),
        "industry_vertical": raw.get("industry_vertical"),
        "company_stage": raw.get("company_stage"),
        "compensation_min": _coerce_int(raw.get("compensation_min")),
        "compensation_max": _coerce_int(raw.get("compensation_max")),
        "compensation_currency": raw.get("compensation_currency"),
        "compensation_period": raw.get("compensation_period"),
        "equity_mentioned": bool(raw.get("equity_mentioned", False)),
        "tech_stack": raw.get("tech_stack") or [],
        "urgency_score": float(raw.get("urgency_score", 0.0)),
        "confidence": float(raw.get("confidence", 0.0)),
        "sentiment_score": 0.0,
        "llm_classified": True,
    }


def classify_post(post: dict[str, Any]) -> dict[str, Any]:
    """Classify a single Reddit post via Claude Haiku. Raises on failure."""
    client = _get_client()
    result = _llm_classify_one(client, post)
    logger.info(
        "LLM classified %s: category=%s domain=%s conf=%.2f",
        post.get("post_id"), result["post_category"], result["domain"],
        result["confidence"],
    )
    return result


# ---------------------------------------------------------------------------
# Batch entry point
# ---------------------------------------------------------------------------
def _pre_filter_reject(post: dict[str, Any]) -> dict[str, Any] | None:
    """Return a fully-formed classification when the post is obviously not a job."""
    category = _quick_reject_category(
        post.get("title", ""),
        post.get("body", "") or "",
    )
    if not category:
        return None
    return {
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
    }


def _rule_fallback(post: dict[str, Any]) -> dict[str, Any]:
    """Run the high-precision rule fallback. Always succeeds."""
    result = rule_enrich_post(post)
    result["llm_classified"] = False
    return result


def classify_posts_batch(
    posts: list[dict[str, Any]],
    max_workers: int = 20,
    breaker: LLMCircuitBreaker | None = None,
) -> list[dict[str, Any]]:
    """Classify a list of posts. Never raises.

    Strategy:
      1. Pre-filter obvious non-jobs without calling the API.
      2. For the rest, fan out to the LLM with a thread pool.
      3. Each call retries up to 4 times on transient errors.
      4. Track post-retry failures in the circuit breaker. When it trips,
         stop the pool and route the remainder through ``_rule_fallback``.
      5. Any individual exception that escapes the retry loop also routes
         that post through the rule fallback and increments the breaker.

    The returned list always covers every input post.
    """
    if not posts:
        return []

    if breaker is None:
        breaker = LLMCircuitBreaker(threshold=5, name="llm_sieve")

    if not openai_available():
        logger.warning(
            "ANTHROPIC_API_KEY not set — routing all %d posts through rule fallback.",
            len(posts),
        )
        breaker.force_trip("ANTHROPIC_API_KEY missing")
        return [_rule_fallback(p) for p in posts]

    # ── Pre-filter ────────────────────────────────────────────────────────
    results: list[dict[str, Any]] = []
    to_classify: list[dict[str, Any]] = []
    for post in posts:
        rejected = _pre_filter_reject(post)
        if rejected:
            results.append(rejected)
        else:
            to_classify.append(post)

    logger.info(
        "Pre-filter: %d skipped, %d sent to LLM (of %d total).",
        len(results), len(to_classify), len(posts),
    )

    if not to_classify:
        return results

    client = _get_client()

    # ── Pre-flight probe ─────────────────────────────────────────────────
    # Make ONE call before fanning out. If the LLM is fatally unavailable
    # (bad key, no credit, 4xx), trip the breaker now and route the ENTIRE
    # batch through the rule fallback — wasting a single call instead of a
    # full wave of `max_workers` doomed, retried requests.
    probe_post = to_classify[0]
    try:
        probe_result = _llm_classify_one(client, probe_post)
        breaker.record_success()
        results.append(probe_result)
        remaining = to_classify[1:]
    except Exception as exc:  # noqa: BLE001
        if _is_fatal_llm_error(exc):
            breaker.force_trip(f"pre-flight fatal LLM error: {exc.__class__.__name__}: {exc}")
            logger.error(
                "Pre-flight LLM probe hit a fatal error (%s) — routing all %d posts "
                "through the rule fallback with no further API calls.",
                exc.__class__.__name__, len(to_classify),
            )
            results.extend(_rule_fallback(p) for p in to_classify)
            logger.info(
                "Batch complete (LLM unavailable): %d results, all rule fallback. %s",
                len(results), breaker.status_message(),
            )
            return results
        # Transient probe failure: count it and proceed; the fan-out below will
        # retry/fall back per post as usual.
        logger.warning("Pre-flight probe failed transiently (%s); proceeding.", exc.__class__.__name__)
        breaker.record_failure(exc)
        results.append(_rule_fallback(probe_post))
        remaining = to_classify[1:]

    if not remaining:
        return results

    # ── LLM fan-out with breaker ─────────────────────────────────────────
    from concurrent.futures import ThreadPoolExecutor, as_completed

    completed = 0
    fallback_count = 0

    def _classify_or_skip(post: dict[str, Any]) -> dict[str, Any]:
        """Worker body. Checks the breaker BEFORE making any API call so that
        once the breaker trips (e.g. on a fatal 401/403/credit error), the
        remaining queued posts short-circuit to the rule fallback instead of
        each firing its own doomed request."""
        if breaker.is_tripped():
            return _rule_fallback(post)
        try:
            result = _llm_classify_one(client, post)
            breaker.record_success()
            return result
        except Exception as exc:  # noqa: BLE001
            # A fatal error (bad key, no credit, permission) will fail for every
            # post this run, so trip the breaker NOW rather than after N misses.
            if _is_fatal_llm_error(exc):
                breaker.force_trip(f"fatal LLM error: {exc.__class__.__name__}: {exc}")
                logger.error(
                    "Fatal LLM error on %s — tripping breaker, rest of batch uses "
                    "rule fallback with no further API calls: %s",
                    post.get("post_id"), exc,
                )
            else:
                logger.error(
                    "LLM classification failed for %s after retries: %s",
                    post.get("post_id"), exc,
                )
                breaker.record_failure(exc)
            return _rule_fallback(post)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_classify_or_skip, post): post for post in remaining}
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 — _classify_or_skip never raises, but be safe
                result = _rule_fallback(futures[future])
                logger.error("Unexpected worker error: %s", exc)
            results.append(result)
            if not result.get("llm_classified"):
                fallback_count += 1

            if completed % 50 == 0 or completed == len(remaining):
                logger.info(
                    "Progress: %d/%d (%s) fallback=%d",
                    completed, len(remaining), breaker.status_message(),
                    fallback_count,
                )

    logger.info(
        "Batch complete: %d results (fallback=%d). %s",
        len(results), fallback_count, breaker.status_message(),
    )
    return results


def openai_available() -> bool:
    """Return True if the Anthropic API key is configured."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))
