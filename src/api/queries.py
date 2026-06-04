"""SQL helpers for the dashboard API.

We funnel every read through ``src.db.execute_query`` so connection handling
stays consistent with the rest of the project. The placeholder differs
between Postgres (%s) and SQLite (?), so we ask the db helper for it.

All public functions return plain ``dict`` / list-of-dict — directly
serialisable by Pydantic / FastAPI.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from src.api.filters import (
    FilterParams,
    build_where,
    cutoff_for,
    post_ids_for_techs,
)
from src.db import _is_postgres, _placeholder, execute_query


def _row_dict(row: Any) -> dict:
    """Normalise a row returned by either psycopg2 RealDictCursor or sqlite3."""
    if isinstance(row, dict):
        return dict(row)
    # sqlite3.Row supports keys()
    return {k: row[k] for k in row.keys()}


def _scalar(row: Any) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0]


# ---------------------------------------------------------------------------
# /api/meta — top-bar counters
# ---------------------------------------------------------------------------
def fetch_meta() -> dict:
    total_jobs = _scalar(
        _first(
            execute_query(
                "SELECT COUNT(*) AS n FROM job_classifications WHERE is_job = TRUE",
                fetch=True,
            )
        )
    ) or 0
    total_posts = _scalar(
        _first(execute_query("SELECT COUNT(*) AS n FROM posts", fetch=True))
    ) or 0

    latest_scraped = _scalar(
        _first(execute_query("SELECT MAX(scraped_at) AS m FROM posts", fetch=True))
    )
    latest_classified = _scalar(
        _first(
            execute_query(
                "SELECT MAX(classified_at) AS m FROM job_classifications",
                fetch=True,
            )
        )
    )

    llm_pct_row = _first(
        execute_query(
            """SELECT
                   SUM(CASE WHEN llm_classified THEN 1 ELSE 0 END) * 1.0 /
                   NULLIF(COUNT(*), 0) AS p
               FROM job_classifications""",
            fetch=True,
        )
    )
    llm_pct = float(_scalar(llm_pct_row) or 0) * 100.0

    scams = _scalar(
        _first(
            execute_query(
                "SELECT COUNT(*) AS n FROM job_classifications WHERE is_scam = TRUE",
                fetch=True,
            )
        )
    ) or 0

    return {
        "total_jobs": int(total_jobs),
        "total_posts": int(total_posts),
        "latest_scraped_at": latest_scraped,
        "latest_classified_at": latest_classified,
        "llm_classified_pct": round(llm_pct, 1),
        "scams_flagged": int(scams),
    }


# ---------------------------------------------------------------------------
# /api/filters — facet values
# ---------------------------------------------------------------------------
def fetch_filter_values() -> dict:
    domains = _column(execute_query(
        """SELECT DISTINCT domain FROM job_classifications
           WHERE is_job = TRUE AND domain IS NOT NULL
           ORDER BY domain""",
        fetch=True,
    ))
    job_types = _column(execute_query(
        """SELECT DISTINCT job_type FROM job_classifications
           WHERE is_job = TRUE AND job_type IS NOT NULL
           ORDER BY job_type""",
        fetch=True,
    ))
    seniorities = _column(execute_query(
        """SELECT DISTINCT seniority FROM job_classifications
           WHERE is_job = TRUE AND seniority IS NOT NULL""",
        fetch=True,
    ))
    work_modes = _column(execute_query(
        """SELECT DISTINCT work_mode FROM job_classifications
           WHERE is_job = TRUE AND work_mode IS NOT NULL""",
        fetch=True,
    ))
    techs = _column(execute_query(
        """SELECT technology, COUNT(*) AS n FROM tech_stack
           GROUP BY technology
           ORDER BY n DESC, technology
           LIMIT 200""",
        fetch=True,
    ))
    subs = _column(execute_query(
        """SELECT DISTINCT subreddit FROM posts ORDER BY subreddit""",
        fetch=True,
    ))

    # Sort seniorities in canonical order if known
    canonical_seniority = [
        "Intern", "Junior", "Mid", "Senior", "Staff",
        "Principal", "Lead/Manager", "Director+",
    ]
    seniorities_sorted = (
        [s for s in canonical_seniority if s in seniorities]
        + sorted([s for s in seniorities if s not in canonical_seniority])
    )

    return {
        "domains": domains,
        "job_types": job_types,
        "seniorities": seniorities_sorted,
        "work_modes": work_modes,
        "techs": techs,
        "subreddits": subs,
    }


# ---------------------------------------------------------------------------
# /api/jobs — paginated list + KPI block
# ---------------------------------------------------------------------------
def fetch_jobs(
    params: FilterParams,
    page: int,
    page_size: int,
) -> dict:
    ph = _placeholder()

    # When the user picked tech facets, resolve to post_ids first.
    tech_ids: Optional[list[str]] = None
    if params.tech:
        sql, args = post_ids_for_techs(params.tech, placeholder=ph)
        rows = execute_query(sql, tuple(args), fetch=True)
        tech_ids = [r["post_id"] if isinstance(r, dict) else r[0] for r in rows]

    where, args = build_where(params, placeholder=ph, tech_post_ids=tech_ids)

    # Total
    total_row = _first(execute_query(
        f"""SELECT COUNT(*) AS n
           FROM posts p
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE {where}""",
        tuple(args),
        fetch=True,
    ))
    total = int(_scalar(total_row) or 0)
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, pages))
    offset = (page - 1) * page_size

    items_sql = f"""
        SELECT p.post_id, p.title, p.body, p.subreddit, p.score,
               p.num_comments, p.created_utc, p.post_url,
               jc.domain, jc.seniority, jc.work_mode, jc.job_type,
               jc.post_category, jc.industry_vertical, jc.company_stage,
               jc.compensation_min, jc.compensation_max,
               jc.compensation_currency, jc.compensation_period,
               jc.urgency_score, jc.confidence, jc.llm_classified,
               jc.is_scam
        FROM posts p
        JOIN job_classifications jc ON p.post_id = jc.post_id
        WHERE {where}
        ORDER BY p.created_utc DESC
        LIMIT {ph} OFFSET {ph}
    """
    rows = execute_query(items_sql, tuple(args + [page_size, offset]), fetch=True)
    items = [_row_dict(r) for r in rows]

    # Fetch tech stack for the current page in one query.
    post_ids = [item["post_id"] for item in items]
    tech_map: dict[str, list[str]] = {}
    if post_ids:
        placeholders = ", ".join([ph] * len(post_ids))
        tech_rows = execute_query(
            f"""SELECT post_id, technology FROM tech_stack
               WHERE post_id IN ({placeholders})
               ORDER BY post_id, technology""",
            tuple(post_ids),
            fetch=True,
        )
        for r in tech_rows:
            r = _row_dict(r)
            tech_map.setdefault(r["post_id"], []).append(r["technology"])

    for item in items:
        body = item.pop("body", None)
        item["excerpt"] = (body or "")[:280] if isinstance(body, str) else None
        item["tech_stack"] = tech_map.get(item["post_id"], [])
        # Coerce booleans/numbers from sqlite (which uses 0/1)
        item["is_scam"] = bool(item.get("is_scam")) if item.get("is_scam") is not None else None
        item["llm_classified"] = bool(item.get("llm_classified")) if item.get("llm_classified") is not None else None

    kpis = _compute_kpis(params, where, args)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "kpis": kpis,
    }


def _compute_kpis(params: FilterParams, where: str, args: list) -> dict:
    ph = _placeholder()
    now = datetime.now(tz=timezone.utc)
    day_ago = now.replace(microsecond=0) - __import__("datetime").timedelta(days=1)

    # total_jobs for the filtered slice
    total_jobs = int(_scalar(_first(execute_query(
        f"""SELECT COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where}""",
        tuple(args), fetch=True,
    ))) or 0)

    new_24h = int(_scalar(_first(execute_query(
        f"""SELECT COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND p.created_utc >= {ph}""",
        tuple(args + [day_ago]), fetch=True,
    ))) or 0)

    remote_count = int(_scalar(_first(execute_query(
        f"""SELECT COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND jc.work_mode = 'Remote'""",
        tuple(args), fetch=True,
    ))) or 0)

    top_domain_row = _first(execute_query(
        f"""SELECT jc.domain AS d, COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND jc.domain IS NOT NULL
           GROUP BY jc.domain
           ORDER BY n DESC
           LIMIT 1""",
        tuple(args), fetch=True,
    ))
    top_domain = _row_dict(top_domain_row).get("d") if top_domain_row else None

    tech_skills = int(_scalar(_first(execute_query(
        f"""SELECT COUNT(DISTINCT t.technology) AS n
           FROM tech_stack t
           JOIN posts p ON p.post_id = t.post_id
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE {where}""",
        tuple(args), fetch=True,
    ))) or 0)

    return {
        "total_jobs": total_jobs,
        "new_24h": new_24h,
        "remote_pct": int(round(100 * remote_count / total_jobs)) if total_jobs else 0,
        "top_domain": top_domain,
        "tech_skills": tech_skills,
    }


# ---------------------------------------------------------------------------
# /api/analytics
# ---------------------------------------------------------------------------
def fetch_analytics(params: FilterParams) -> dict:
    ph = _placeholder()
    tech_ids: Optional[list[str]] = None
    if params.tech:
        sql, args = post_ids_for_techs(params.tech, placeholder=ph)
        rows = execute_query(sql, tuple(args), fetch=True)
        tech_ids = [r["post_id"] if isinstance(r, dict) else r[0] for r in rows]
    where, args = build_where(params, placeholder=ph, tech_post_ids=tech_ids)

    # volume over time — group by day
    date_expr = (
        "to_char(p.created_utc, 'YYYY-MM-DD')"
        if _is_postgres() else
        "strftime('%Y-%m-%d', p.created_utc)"
    )
    volume_rows = execute_query(
        f"""SELECT {date_expr} AS d, COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where}
           GROUP BY d
           ORDER BY d""",
        tuple(args), fetch=True,
    )
    volume = [
        {"date": _row_dict(r)["d"], "value": int(_row_dict(r)["n"])}
        for r in volume_rows
    ]

    top_subreddits = _label_value(execute_query(
        f"""SELECT p.subreddit AS l, COUNT(*) AS v
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where}
           GROUP BY p.subreddit
           ORDER BY v DESC
           LIMIT 10""",
        tuple(args), fetch=True,
    ))

    domain_breakdown = _label_value(execute_query(
        f"""SELECT jc.domain AS l, COUNT(*) AS v
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND jc.domain IS NOT NULL
           GROUP BY jc.domain
           ORDER BY v DESC""",
        tuple(args), fetch=True,
    ))

    work_mode_split = _label_value(execute_query(
        f"""SELECT jc.work_mode AS l, COUNT(*) AS v
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND jc.work_mode IS NOT NULL
           GROUP BY jc.work_mode
           ORDER BY v DESC""",
        tuple(args), fetch=True,
    ))

    seniority_breakdown = _label_value(execute_query(
        f"""SELECT jc.seniority AS l, COUNT(*) AS v
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND jc.seniority IS NOT NULL
           GROUP BY jc.seniority""",
        tuple(args), fetch=True,
    ))
    job_type_breakdown = _label_value(execute_query(
        f"""SELECT jc.job_type AS l, COUNT(*) AS v
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND jc.job_type IS NOT NULL
           GROUP BY jc.job_type
           ORDER BY v DESC""",
        tuple(args), fetch=True,
    ))

    top_skills = _label_value(execute_query(
        f"""SELECT t.technology AS l, COUNT(*) AS v
           FROM tech_stack t
           JOIN posts p ON p.post_id = t.post_id
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE {where}
           GROUP BY t.technology
           ORDER BY v DESC
           LIMIT 20""",
        tuple(args), fetch=True,
    ))

    # salary by role — only when we have ≥ 5 samples per (domain, seniority).
    salary_sql = (
        f"""SELECT jc.domain AS domain,
                  jc.seniority AS seniority,
                  PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY jc.compensation_min) AS p25,
                  PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY jc.compensation_min) AS median,
                  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY jc.compensation_min) AS p75,
                  COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where}
             AND jc.compensation_min IS NOT NULL
             AND jc.compensation_min > 1000
             AND jc.domain IS NOT NULL
             AND jc.seniority IS NOT NULL
             AND jc.compensation_period = 'annual'
           GROUP BY jc.domain, jc.seniority
           HAVING COUNT(*) >= 5
           ORDER BY median DESC"""
        if _is_postgres()
        else
        # SQLite has no PERCENTILE_CONT; fall back to AVG so the chart still
        # renders something locally.
        f"""SELECT jc.domain AS domain,
                  jc.seniority AS seniority,
                  CAST(AVG(jc.compensation_min) AS INTEGER) AS p25,
                  CAST(AVG(jc.compensation_min) AS INTEGER) AS median,
                  CAST(AVG(jc.compensation_min) AS INTEGER) AS p75,
                  COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where}
             AND jc.compensation_min IS NOT NULL
             AND jc.compensation_min > 1000
             AND jc.domain IS NOT NULL
             AND jc.seniority IS NOT NULL
             AND jc.compensation_period = 'annual'
           GROUP BY jc.domain, jc.seniority
           HAVING COUNT(*) >= 5
           ORDER BY median DESC"""
    )
    salary_rows = execute_query(salary_sql, tuple(args), fetch=True)
    salary_by_role = [
        {
            "domain": _row_dict(r)["domain"],
            "seniority": _row_dict(r)["seniority"],
            "median": int(_row_dict(r)["median"] or 0),
            "p25": int(_row_dict(r)["p25"] or 0),
            "p75": int(_row_dict(r)["p75"] or 0),
            "sample_size": int(_row_dict(r)["n"]),
        }
        for r in salary_rows
    ]

    return {
        "volume_over_time": volume,
        "top_subreddits": top_subreddits,
        "domain_breakdown": domain_breakdown,
        "work_mode_split": work_mode_split,
        "seniority_breakdown": seniority_breakdown,
        "job_type_breakdown": job_type_breakdown,
        "top_skills": top_skills,
        "salary_by_role": salary_by_role,
    }


# ---------------------------------------------------------------------------
# /api/tech-trends
# ---------------------------------------------------------------------------
def fetch_tech_trends(params: FilterParams) -> dict:
    ph = _placeholder()
    tech_ids: Optional[list[str]] = None
    if params.tech:
        sql, args = post_ids_for_techs(params.tech, placeholder=ph)
        rows = execute_query(sql, tuple(args), fetch=True)
        tech_ids = [r["post_id"] if isinstance(r, dict) else r[0] for r in rows]
    where, args = build_where(params, placeholder=ph, tech_post_ids=tech_ids)

    # top-8 techs in the filtered slice
    top8_rows = execute_query(
        f"""SELECT t.technology AS tech, COUNT(*) AS n
           FROM tech_stack t
           JOIN posts p ON p.post_id = t.post_id
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE {where}
           GROUP BY t.technology
           ORDER BY n DESC
           LIMIT 8""",
        tuple(args), fetch=True,
    )
    top8 = [_row_dict(r)["tech"] for r in top8_rows]

    weekly_demand: list[dict] = []
    if top8:
        placeholders = ", ".join([ph] * len(top8))
        week_expr = (
            "to_char(date_trunc('week', p.created_utc), 'IYYY-\"W\"IW')"
            if _is_postgres() else
            "strftime('%Y-W%W', p.created_utc)"
        )
        rows = execute_query(
            f"""SELECT {week_expr} AS week, t.technology AS tech, COUNT(*) AS n
               FROM tech_stack t
               JOIN posts p ON p.post_id = t.post_id
               JOIN job_classifications jc ON p.post_id = jc.post_id
               WHERE {where} AND t.technology IN ({placeholders})
               GROUP BY week, t.technology
               ORDER BY week, tech""",
            tuple(args + top8), fetch=True,
        )
        weekly_demand = [
            {
                "week": _row_dict(r)["week"],
                "tech": _row_dict(r)["tech"],
                "count": int(_row_dict(r)["n"]),
            }
            for r in rows
        ]

    # heatmap — top 20 techs × all domains in the slice
    top20_rows = execute_query(
        f"""SELECT t.technology AS tech, COUNT(*) AS n
           FROM tech_stack t
           JOIN posts p ON p.post_id = t.post_id
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE {where}
           GROUP BY t.technology
           ORDER BY n DESC
           LIMIT 20""",
        tuple(args), fetch=True,
    )
    top20 = [_row_dict(r)["tech"] for r in top20_rows]

    domain_rows = execute_query(
        f"""SELECT jc.domain AS d, COUNT(*) AS n
           FROM posts p JOIN job_classifications jc ON p.post_id=jc.post_id
           WHERE {where} AND jc.domain IS NOT NULL
           GROUP BY jc.domain
           ORDER BY n DESC""",
        tuple(args), fetch=True,
    )
    domains = [_row_dict(r)["d"] for r in domain_rows]

    matrix: list[list[int]] = [[0] * len(top20) for _ in domains]
    if domains and top20:
        d_placeholders = ", ".join([ph] * len(domains))
        t_placeholders = ", ".join([ph] * len(top20))
        cell_rows = execute_query(
            f"""SELECT jc.domain AS d, t.technology AS tech, COUNT(*) AS n
               FROM tech_stack t
               JOIN posts p ON p.post_id = t.post_id
               JOIN job_classifications jc ON p.post_id = jc.post_id
               WHERE {where}
                 AND jc.domain IN ({d_placeholders})
                 AND t.technology IN ({t_placeholders})
               GROUP BY jc.domain, t.technology""",
            tuple(args + domains + top20), fetch=True,
        )
        d_idx = {d: i for i, d in enumerate(domains)}
        t_idx = {t: i for i, t in enumerate(top20)}
        for r in cell_rows:
            r = _row_dict(r)
            matrix[d_idx[r["d"]]][t_idx[r["tech"]]] = int(r["n"])

    # tech pairs — SQL self-join with ts1.tech < ts2.tech
    pair_rows = execute_query(
        f"""SELECT t1.technology AS a, t2.technology AS b, COUNT(*) AS n
           FROM tech_stack t1
           JOIN tech_stack t2 ON t1.post_id = t2.post_id AND t1.technology < t2.technology
           JOIN posts p ON p.post_id = t1.post_id
           JOIN job_classifications jc ON p.post_id = jc.post_id
           WHERE {where}
           GROUP BY t1.technology, t2.technology
           ORDER BY n DESC
           LIMIT 15""",
        tuple(args), fetch=True,
    )
    pairs = [
        {"a": _row_dict(r)["a"], "b": _row_dict(r)["b"], "count": int(_row_dict(r)["n"])}
        for r in pair_rows
    ]

    return {
        "weekly_demand": weekly_demand,
        "heatmap": {"domains": domains, "techs": top20, "matrix": matrix},
        "pairs": pairs,
    }


# ---------------------------------------------------------------------------
# /api/subreddit-health
# ---------------------------------------------------------------------------
def fetch_subreddit_health(limit: int = 100) -> dict:
    rows = execute_query(
        """SELECT p.subreddit                          AS subreddit,
                  COUNT(*)                             AS posts_scraped,
                  SUM(CASE WHEN jc.is_job   THEN 1 ELSE 0 END) AS jobs_found,
                  SUM(CASE WHEN jc.is_scam THEN 1 ELSE 0 END) AS scams_flagged,
                  MAX(p.scraped_at)                    AS last_scraped
           FROM posts p
           LEFT JOIN job_classifications jc ON p.post_id = jc.post_id
           GROUP BY p.subreddit""",
        fetch=True,
    )
    items = []
    for r in rows:
        r = _row_dict(r)
        scraped = int(r["posts_scraped"] or 0)
        jobs = int(r["jobs_found"] or 0)
        items.append({
            "subreddit": r["subreddit"],
            "posts_scraped": scraped,
            "jobs_found": jobs,
            "scams_flagged": int(r["scams_flagged"] or 0),
            "dedup_rate": None,
            "last_scraped": r["last_scraped"],
            "job_rate": round(jobs / scraped, 3) if scraped else None,
        })
    items.sort(key=lambda x: (x["jobs_found"], x["posts_scraped"]), reverse=True)
    items = items[:limit]
    return {"items": items, "as_of": datetime.now(tz=timezone.utc)}


# ---------------------------------------------------------------------------
# Tiny row helpers
# ---------------------------------------------------------------------------
def _first(rows):
    return rows[0] if rows else None


def _column(rows) -> list[str]:
    return [
        next(iter(_row_dict(r).values()))
        for r in rows
    ]


def _label_value(rows) -> list[dict]:
    out = []
    for r in rows:
        r = _row_dict(r)
        out.append({"label": str(r["l"]), "value": float(r["v"])})
    return out
