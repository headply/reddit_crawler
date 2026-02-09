"""NLP enrichment module for job post classification.

Uses rule-based pattern matching and TextBlob for sentiment analysis
to classify and enrich scraped Reddit posts.
"""

import logging
import re
from typing import Any, Optional

from textblob import TextBlob

from src.config import (
    DOMAIN_PATTERNS,
    JOB_NEGATIVE_PATTERNS,
    JOB_POSITIVE_PATTERNS,
    JOB_TYPE_PATTERNS,
    SENIORITY_PATTERNS,
    TECH_KEYWORDS,
    URGENCY_PATTERNS,
    WORK_MODE_PATTERNS,
)

logger = logging.getLogger(__name__)


def _match_patterns(text: str, patterns: dict[str, list[str]]) -> Optional[str]:
    """Match text against a dictionary of patterns and return the best match.

    Args:
        text: Text to search in (lowercased).
        patterns: Dictionary mapping category names to keyword lists.

    Returns:
        Best matching category name, or None.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in patterns.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[category] = count
    if scores:
        return max(scores, key=scores.get)  # type: ignore[arg-type]
    return None


def classify_is_job(title: str, body: str) -> bool:
    """Determine if a post represents a real job opportunity.

    Uses keyword matching with positive and negative signals.
    Posts from hiring-focused subreddits get a bonus.

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        True if the post appears to be a job listing.
    """
    text = f"{title} {body}".lower()

    positive_score = sum(1 for p in JOB_POSITIVE_PATTERNS if p in text)
    negative_score = sum(1 for p in JOB_NEGATIVE_PATTERNS if p in text)

    # Title-based signals are stronger
    title_lower = title.lower()
    if any(p in title_lower for p in ["[hiring]", "hiring", "job opening", "position"]):
        positive_score += 3

    if any(p in title_lower for p in ["[for hire]", "hire me", "looking for work"]):
        negative_score += 3

    return positive_score > negative_score


def classify_job_type(title: str, body: str) -> Optional[str]:
    """Classify the employment type of a job post.

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        Job type string or None.
    """
    return _match_patterns(f"{title} {body}", JOB_TYPE_PATTERNS)


def classify_seniority(title: str, body: str) -> Optional[str]:
    """Classify the seniority level of a job post.

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        Seniority level string or None.
    """
    return _match_patterns(f"{title} {body}", SENIORITY_PATTERNS)


def classify_domain(title: str, body: str) -> Optional[str]:
    """Classify the professional domain of a job post.

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        Domain string or None.
    """
    return _match_patterns(f"{title} {body}", DOMAIN_PATTERNS)


def classify_work_mode(title: str, body: str) -> Optional[str]:
    """Classify work arrangement (Remote/Hybrid/On-site).

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        Work mode string or None.
    """
    return _match_patterns(f"{title} {body}", WORK_MODE_PATTERNS)


def extract_tech_stack(title: str, body: str) -> list[str]:
    """Extract mentioned technologies from post text.

    Uses keyword matching against a curated technology dictionary.

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        List of unique technology names found.
    """
    text = f" {title} {body} ".lower()
    found: list[str] = []
    for tech_name, keywords in TECH_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            found.append(tech_name)
    return sorted(set(found))


def compute_sentiment(title: str, body: str) -> float:
    """Compute sentiment polarity of the post.

    Uses TextBlob sentiment analysis. Score ranges from -1.0 (negative)
    to 1.0 (positive).

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        Sentiment polarity score.
    """
    text = f"{title}. {body}"
    blob = TextBlob(text)
    return round(blob.sentiment.polarity, 3)


def compute_urgency(title: str, body: str) -> float:
    """Compute urgency score based on keyword heuristics.

    Score is 0.0 (not urgent) to 1.0 (very urgent), calculated as
    the ratio of urgency keywords found to total urgency patterns.

    Args:
        title: Post title.
        body: Post body text.

    Returns:
        Urgency score between 0.0 and 1.0.
    """
    text = f"{title} {body}".lower()
    matches = sum(1 for p in URGENCY_PATTERNS if p in text)
    score = min(matches / max(len(URGENCY_PATTERNS) * 0.3, 1), 1.0)
    return round(score, 3)


def enrich_post(post: dict[str, Any]) -> dict[str, Any]:
    """Run full NLP enrichment pipeline on a single post.

    Performs classification, tech stack extraction, sentiment analysis,
    and urgency scoring.

    Args:
        post: Dictionary containing post_id, title, and body.

    Returns:
        Dictionary with classification results, tech stack, and scores.
    """
    title = post.get("title", "")
    body = post.get("body", "")
    post_id = post["post_id"]

    is_job = classify_is_job(title, body)

    classification: dict[str, Any] = {
        "post_id": post_id,
        "is_job": is_job,
        "job_type": classify_job_type(title, body) if is_job else None,
        "seniority": classify_seniority(title, body) if is_job else None,
        "domain": classify_domain(title, body) if is_job else None,
        "work_mode": classify_work_mode(title, body) if is_job else None,
        "sentiment_score": compute_sentiment(title, body),
        "urgency_score": compute_urgency(title, body) if is_job else 0.0,
        "tech_stack": extract_tech_stack(title, body) if is_job else [],
    }

    logger.debug(
        "Enriched %s: is_job=%s, domain=%s, techs=%s",
        post_id, is_job, classification["domain"],
        classification["tech_stack"],
    )

    return classification
