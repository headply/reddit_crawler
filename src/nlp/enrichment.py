"""High-precision rule-based fallback classifier.

When the LLM is unreachable, this module classifies a Reddit post using a
strict, precision-first rule layer. The design priority is: never classify
a question, advice request, rant, or meta-thread as a hiring or for-hire
opportunity. False negatives are cheap (the LLM upgrades them on the next
run via `reclassify_pending`); false positives pollute the dashboard.

Pipeline:
  1. Hard veto layer            → advice_request / discussion / rant / meme
  2. Title-prefix gate          → hiring / for_hire (title tag REQUIRED)
  3. Length floor               → < 80 chars and not in for_hire_focused → other
  4. Domain / job-type / etc.   → only computed when category is hiring/for_hire
  5. Stamp confidence = 0.55    → flags row for LLM upgrade later
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from src.config import (
    DOMAIN_PATTERNS,
    JOB_NEGATIVE_PATTERNS,
    JOB_TYPE_PATTERNS,
    SENIORITY_PATTERNS,
    SUBREDDIT_GROUPS,
    TECH_KEYWORDS,
    URGENCY_PATTERNS,
    WORK_MODE_PATTERNS,
)

logger = logging.getLogger(__name__)

# Confidence stamped on every rule-classified row. Below 0.60 so the
# `reclassify_pending` Airflow task picks it up when the LLM returns,
# and so the dashboard can render a "rule-classified" chip.
RULE_CONFIDENCE = 0.55

# ---------------------------------------------------------------------------
# Hard veto patterns — these short-circuit to a non-job category.
# ---------------------------------------------------------------------------
_QUESTION_PREFIXES = (
    "who ", "what ", "when ", "where ", "why ", "how ",
    "should i", "is it", "are there", "does anyone", "has anyone",
    "can someone", "anyone else", "am i", "would you", "thinking about",
    "advice", "help ",
)
_DISCUSSION_MARKERS = (
    "[meta]", "[discussion]", "[mod]", "weekly thread", "daily thread",
    "megathread", "weekly hiring thread", "weekly job thread",
    "monthly thread", "biweekly thread",
)
_RANT_MARKERS = (
    "rant", "vent", "frustrated", "pissed", "i quit", "quit my job",
    "laid off", "got fired", "unemployed", "job search update",
    "applied to 100", "applied to 200", "applied to 500",
    "interview experience", "interview process", "am i cooked",
    "should i accept", "should i take", "which offer", "comparing offers",
    "salary negotiation", "lowball", "counter offer", "ghosted",
    "rejected", "recruiter ghosted",
)

# Title tags that REQUIRE this exact wording in the title for the post to
# be classified as a real opportunity. Body-only hiring signals are
# ignored — they have far too many false positives.
_HIRING_TITLE_TAGS = (
    "[hiring]", "hiring", "we're hiring", "we are hiring", "now hiring",
    "looking to hire", "open role", "open position", "job opening",
    "open positions",
)
_FOR_HIRE_TITLE_TAGS = (
    "[for hire]", "for hire", "available for hire", "looking for work",
    "looking for clients", "open to work", "open to freelance",
    "freelance available",
)
_GIG_TITLE_TAGS = (
    "[gig]", "[task]", "freelance gig", "one-off project", "small project",
    "quick gig", "paid project",
)

_LENGTH_FLOOR = 80
_FOR_HIRE_FOCUSED_SUBS = {s.lower() for s in SUBREDDIT_GROUPS.get("for_hire_focused", [])}


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _title_starts_with(title: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if title.startswith(prefix):
            return True
    return False


def _hard_veto_category(title: str, body: str) -> Optional[str]:
    """Return a non-job post_category when the post should be vetoed.

    Returns one of: 'advice_request', 'discussion', 'rant', 'other', or None
    (meaning the veto layer did not match and downstream rules apply).
    """
    title_n = _normalise(title)
    body_n = _normalise(body)
    total_len = len(title_n) + len(body_n)

    if total_len < 30:
        return "other"

    # Discussion / meta threads — checked before everything else because
    # "weekly hiring thread" contains the word "hiring".
    if _has_any(title_n, _DISCUSSION_MARKERS):
        return "discussion"

    # Rants and interview / offer / job-search talk.
    if _has_any(title_n, _RANT_MARKERS):
        return "rant"

    # Explicit question-leading title.
    if title_n.startswith("?"):
        return "advice_request"
    if _title_starts_with(title_n, _QUESTION_PREFIXES):
        return "advice_request"

    # Title is a question mark and contains NO hiring marker → discussion.
    if title_n.endswith("?") and not (
        _has_any(title_n, _HIRING_TITLE_TAGS)
        or _has_any(title_n, _FOR_HIRE_TITLE_TAGS)
        or _has_any(title_n, _GIG_TITLE_TAGS)
    ):
        return "advice_request"

    return None


def _category_from_title_tag(title_n: str) -> Optional[str]:
    """Return 'hiring' / 'for_hire' / 'gig_freelance' if the title carries the tag."""
    # For-hire is checked first because "[hiring]" appears as a substring of
    # nothing for-hire-related, but "for hire" + "hire" overlap requires
    # ordering. We check the more specific tag first.
    if _has_any(title_n, _FOR_HIRE_TITLE_TAGS):
        return "for_hire"
    if _has_any(title_n, _GIG_TITLE_TAGS):
        return "gig_freelance"
    if _has_any(title_n, _HIRING_TITLE_TAGS):
        return "hiring"
    return None


def _match_patterns(text: str, patterns: dict[str, list[str]]) -> Optional[str]:
    """Return the category with the most keyword matches, or None."""
    scores: dict[str, int] = {}
    for category, keywords in patterns.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            scores[category] = count
    if not scores:
        return None
    return max(scores, key=lambda k: scores[k])


def _extract_tech_stack(text: str) -> list[str]:
    found: list[str] = []
    for tech_name, keywords in TECH_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(tech_name)
    return sorted(set(found))


def _compute_urgency(text: str) -> float:
    matches = sum(1 for p in URGENCY_PATTERNS if p in text)
    score = min(matches / max(len(URGENCY_PATTERNS) * 0.3, 1), 1.0)
    return round(score, 3)


def _has_negative_signal(text: str) -> bool:
    return sum(1 for p in JOB_NEGATIVE_PATTERNS if p in text) >= 2


def classify_post_fallback(
    title: str,
    body: str,
    subreddit: Optional[str] = None,
) -> dict[str, Any]:
    """Pure classification — no DB writes.

    Returns the same dict shape as the LLM classifier (minus post_id), so
    `enrich_post` can wrap it for storage.
    """
    title_n = _normalise(title)
    body_n = _normalise(body)
    full = f"{title_n} {body_n}"
    sub_lower = (subreddit or "").lower()
    total_len = len(title_n) + len(body_n)

    base: dict[str, Any] = {
        "is_job": False,
        "post_category": "other",
        "job_type": None,
        "seniority": None,
        "domain": None,
        "work_mode": None,
        "industry_vertical": None,
        "company_stage": None,
        "compensation_min": None,
        "compensation_max": None,
        "compensation_currency": None,
        "compensation_period": None,
        "equity_mentioned": False,
        "is_scam": None,
        "scam_reasons": None,
        "sentiment_score": 0.0,
        "urgency_score": 0.0,
        "tech_stack": [],
        "confidence": RULE_CONFIDENCE,
    }

    # ── 1. Hard veto ──────────────────────────────────────────────────────
    veto = _hard_veto_category(title, body)
    if veto:
        base["post_category"] = veto
        return base

    # ── 2. Title-tag requirement ─────────────────────────────────────────
    category = _category_from_title_tag(title_n)
    if category is None:
        # No hiring tag in the title → not a job. Mark generic non-job
        # category (we do not try to distinguish discussion vs other here).
        base["post_category"] = "other"
        return base

    # ── 3. Length floor (skipped for hire-focused subs) ─────────────────
    if total_len < _LENGTH_FLOOR and sub_lower not in _FOR_HIRE_FOCUSED_SUBS:
        base["post_category"] = "other"
        return base

    # ── 4. Strong negative signal ────────────────────────────────────────
    if _has_negative_signal(full):
        # Two or more "rejected / interview / am-i-cooked" markers despite a
        # hiring tag in the title (rare but happens) → safer to treat as
        # discussion than to surface a false-positive.
        base["post_category"] = "discussion"
        return base

    # ── 5. Real opportunity — fill in attributes ────────────────────────
    base["is_job"] = True
    base["post_category"] = category
    base["job_type"] = (
        _match_patterns(full, JOB_TYPE_PATTERNS)
        or ("Freelance" if category == "for_hire" else None)
    )
    base["seniority"] = _match_patterns(full, SENIORITY_PATTERNS)
    base["domain"] = _match_patterns(full, DOMAIN_PATTERNS)
    base["work_mode"] = _match_patterns(full, WORK_MODE_PATTERNS)
    base["tech_stack"] = _extract_tech_stack(full)
    base["urgency_score"] = _compute_urgency(full)

    return base


def enrich_post(post: dict[str, Any]) -> dict[str, Any]:
    """Public entrypoint matching the legacy signature.

    Args:
        post: dict with at least post_id, title, body. Optional subreddit.

    Returns:
        Classification dict (includes post_id) ready for
        ``src.db.insert_classification`` and ``insert_tech_stack``.
    """
    title = post.get("title", "")
    body = post.get("body", "") or ""
    sub = post.get("subreddit")
    post_id = post["post_id"]

    result = classify_post_fallback(title, body, sub)
    result["post_id"] = post_id
    return result
