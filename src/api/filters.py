"""Filter parameters shared by every endpoint.

The frontend serialises filters as a single object; on the wire each
multi-valued facet is sent as a comma-separated list so URLs stay short
and shareable (e.g. ?domain=Software%20Engineering,Data%20%26%20Analytics).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import Query

DateRange = Literal["today", "7d", "30d", "90d", "all"]


def _split_csv(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


# Valid post categories that mean "a real opportunity".
_JOB_CATEGORIES = ("hiring", "for_hire", "gig_freelance")
# Default: hiring + gigs only. ``for_hire`` (people pitching themselves)
# is hidden by default because it's a different audience than job seekers
# browsing for openings.
DEFAULT_CATEGORIES: tuple[str, ...] = ("hiring", "gig_freelance")


@dataclass(frozen=True)
class FilterParams:
    search: Optional[str] = None
    domain: list[str] = field(default_factory=list)
    job_type: list[str] = field(default_factory=list)
    seniority: list[str] = field(default_factory=list)
    work_mode: list[str] = field(default_factory=list)
    tech: list[str] = field(default_factory=list)
    subreddit: list[str] = field(default_factory=list)
    categories: list[str] = field(
        default_factory=lambda: list(DEFAULT_CATEGORIES)
    )
    date_range: DateRange = "30d"
    exclude_scams: bool = True
    min_confidence: float = 0.0


def filter_params(
    search: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    job_type: Optional[str] = Query(default=None),
    seniority: Optional[str] = Query(default=None),
    work_mode: Optional[str] = Query(default=None),
    tech: Optional[str] = Query(default=None),
    subreddit: Optional[str] = Query(default=None),
    categories: Optional[str] = Query(default=None),
    date_range: DateRange = Query(default="30d"),
    exclude_scams: bool = Query(default=True),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
) -> FilterParams:
    """FastAPI dependency that parses the shared filter query string."""
    cats = _split_csv(categories)
    if not cats:
        cats = list(DEFAULT_CATEGORIES)
    # Reject unknown categories silently rather than 400-ing.
    cats = [c for c in cats if c in _JOB_CATEGORIES]
    if not cats:
        cats = list(DEFAULT_CATEGORIES)
    return FilterParams(
        search=(search or "").strip() or None,
        domain=_split_csv(domain),
        job_type=_split_csv(job_type),
        seniority=_split_csv(seniority),
        work_mode=_split_csv(work_mode),
        tech=_split_csv(tech),
        subreddit=_split_csv(subreddit),
        categories=cats,
        date_range=date_range,
        exclude_scams=exclude_scams,
        min_confidence=min_confidence,
    )


def cutoff_for(date_range: DateRange) -> datetime:
    now = datetime.now(tz=timezone.utc)
    if date_range == "today":
        return now - timedelta(days=1)
    if date_range == "7d":
        return now - timedelta(days=7)
    if date_range == "30d":
        return now - timedelta(days=30)
    if date_range == "90d":
        return now - timedelta(days=90)
    return datetime(2000, 1, 1, tzinfo=timezone.utc)


def build_where(
    params: FilterParams,
    *,
    require_is_job: bool = True,
    placeholder: str = "%s",
    tech_post_ids: Optional[list[str]] = None,
) -> tuple[str, list]:
    """Return (where_clause, params_list) for a query joining posts + jc.

    The caller is expected to use aliases ``p`` (posts) and ``jc``
    (job_classifications). ``tech_post_ids`` is the result of a separate
    ``SELECT post_id FROM tech_stack WHERE technology IN (...)`` query —
    we filter the main query with ``p.post_id IN (...)`` when the user
    selected tech facets.
    """
    clauses: list[str] = []
    args: list = []

    if require_is_job:
        cats = params.categories or list(DEFAULT_CATEGORIES)
        placeholders = ", ".join([placeholder] * len(cats))
        clauses.append(f"jc.post_category IN ({placeholders})")
        args.extend(cats)

    if params.exclude_scams:
        clauses.append("COALESCE(jc.is_scam, FALSE) = FALSE")

    if params.min_confidence > 0:
        clauses.append(f"COALESCE(jc.confidence, 0) >= {placeholder}")
        args.append(params.min_confidence)

    clauses.append(f"p.created_utc >= {placeholder}")
    args.append(cutoff_for(params.date_range))

    if params.search:
        like = f"%{params.search.lower()}%"
        clauses.append(
            f"(LOWER(p.title) LIKE {placeholder} OR LOWER(COALESCE(p.body,'')) LIKE {placeholder})"
        )
        args.extend([like, like])

    def _in(column: str, values: list[str]) -> None:
        if not values:
            return
        placeholders = ", ".join([placeholder] * len(values))
        clauses.append(f"{column} IN ({placeholders})")
        args.extend(values)

    _in("jc.domain", params.domain)
    _in("jc.job_type", params.job_type)
    _in("jc.seniority", params.seniority)
    _in("jc.work_mode", params.work_mode)
    _in("p.subreddit", params.subreddit)

    if tech_post_ids is not None:
        if not tech_post_ids:
            clauses.append("1 = 0")  # no posts will match
        else:
            placeholders = ", ".join([placeholder] * len(tech_post_ids))
            clauses.append(f"p.post_id IN ({placeholders})")
            args.extend(tech_post_ids)

    where = " AND ".join(clauses) if clauses else "TRUE"
    return where, args


def post_ids_for_techs(techs: list[str], placeholder: str = "%s") -> tuple[str, list]:
    """SQL fragment for selecting post_ids that mention ALL the given techs.

    We use HAVING COUNT(DISTINCT technology) = N so a multi-tech filter is
    treated as a conjunction (AND) — the user wants posts that mention
    every selected tech.
    """
    placeholders = ", ".join([placeholder] * len(techs))
    sql = (
        f"SELECT post_id FROM tech_stack "
        f"WHERE technology IN ({placeholders}) "
        f"GROUP BY post_id "
        f"HAVING COUNT(DISTINCT technology) = {placeholder}"
    )
    args = list(techs) + [len(techs)]
    return sql, args
