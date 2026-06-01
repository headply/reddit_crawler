"""SQL-backed data loaders for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any

import pandas as pd
import streamlit as st

from src.db import _is_postgres, _placeholder, execute_query, get_connection


@dataclass(frozen=True)
class FilterOptions:
    """Selectable filter values."""
    domains: list[str]
    job_types: list[str]
    seniorities: list[str]
    work_modes: list[str]
    tech_stack: list[str]
    subreddits: list[str]
    industry_verticals: list[str]
    company_stages: list[str]


@dataclass(frozen=True)
class FilterState:
    """Snapshot of dashboard filters."""
    start_date: date
    end_date: date
    keyword: str
    domains: tuple[str, ...]
    job_types: tuple[str, ...]
    seniorities: tuple[str, ...]
    work_modes: tuple[str, ...]
    tech_stack: tuple[str, ...]
    subreddits: tuple[str, ...]
    industry_verticals: tuple[str, ...]
    company_stages: tuple[str, ...]
    min_compensation: int | None
    include_scam: bool


def _bool_true() -> str:
    return "TRUE" if _is_postgres() else "1"


def _bool_false() -> str:
    return "FALSE" if _is_postgres() else "0"


def _format_dt(value: datetime) -> Any:
    if _is_postgres():
        return value
    return value.isoformat()


def _build_where(filters: FilterState, jobs_only: bool = True) -> tuple[str, list[Any]]:
    """Build WHERE clause and parameters for filtered queries."""
    conditions: list[str] = ["COALESCE(p.dedup_status, 'unique') = 'unique'"]
    params: list[Any] = []
    ph = _placeholder()

    if jobs_only:
        conditions.append(f"jc.is_job = {_bool_true()}")

    if not filters.include_scam:
        conditions.append(f"COALESCE(jc.is_scam, {_bool_false()}) = {_bool_false()}")

    start_dt = datetime.combine(filters.start_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(filters.end_date, time.max, tzinfo=timezone.utc)
    conditions.append(f"p.created_utc >= {ph}")
    conditions.append(f"p.created_utc <= {ph}")
    params.extend([_format_dt(start_dt), _format_dt(end_dt)])

    if filters.keyword:
        if _is_postgres():
            conditions.append(f"(p.title ILIKE {ph} OR p.body ILIKE {ph})")
            params.extend([f"%{filters.keyword}%", f"%{filters.keyword}%"])
        else:
            conditions.append(f"(lower(p.title) LIKE {ph} OR lower(p.body) LIKE {ph})")
            kw = f"%{filters.keyword.lower()}%"
            params.extend([kw, kw])

    if filters.domains:
        placeholders = ",".join([ph] * len(filters.domains))
        conditions.append(f"jc.domain IN ({placeholders})")
        params.extend(filters.domains)

    if filters.job_types:
        placeholders = ",".join([ph] * len(filters.job_types))
        conditions.append(f"jc.job_type IN ({placeholders})")
        params.extend(filters.job_types)

    if filters.seniorities:
        placeholders = ",".join([ph] * len(filters.seniorities))
        conditions.append(f"jc.seniority IN ({placeholders})")
        params.extend(filters.seniorities)

    if filters.work_modes:
        placeholders = ",".join([ph] * len(filters.work_modes))
        conditions.append(f"jc.work_mode IN ({placeholders})")
        params.extend(filters.work_modes)

    if filters.industry_verticals:
        placeholders = ",".join([ph] * len(filters.industry_verticals))
        conditions.append(f"jc.industry_vertical IN ({placeholders})")
        params.extend(filters.industry_verticals)

    if filters.company_stages:
        placeholders = ",".join([ph] * len(filters.company_stages))
        conditions.append(f"jc.company_stage IN ({placeholders})")
        params.extend(filters.company_stages)

    if filters.subreddits:
        placeholders = ",".join([ph] * len(filters.subreddits))
        conditions.append(f"p.subreddit IN ({placeholders})")
        params.extend(filters.subreddits)

    if filters.min_compensation is not None:
        conditions.append(f"jc.compensation_min >= {ph}")
        params.append(filters.min_compensation)

    if filters.tech_stack:
        placeholders = ",".join([ph] * len(filters.tech_stack))
        conditions.append(
            "EXISTS (SELECT 1 FROM tech_stack ts "
            f"WHERE ts.post_id = p.post_id AND ts.technology IN ({placeholders}))"
        )
        params.extend(filters.tech_stack)

    where_sql = " AND ".join(conditions) if conditions else "1=1"
    return where_sql, params


@st.cache_data(ttl=300)
def load_filter_options() -> FilterOptions:
    """Load distinct filter values from the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        def _distinct(query: str) -> list[str]:
            cursor.execute(query)
            values = [row[0] for row in cursor.fetchall() if row[0]]
            return sorted(set(values))

        domains = _distinct(
            """SELECT DISTINCT jc.domain
               FROM job_classifications jc
               JOIN posts p ON p.post_id = jc.post_id
               WHERE jc.domain IS NOT NULL"""
        )
        job_types = _distinct(
            """SELECT DISTINCT jc.job_type
               FROM job_classifications jc
               JOIN posts p ON p.post_id = jc.post_id
               WHERE jc.job_type IS NOT NULL"""
        )
        seniorities = _distinct(
            """SELECT DISTINCT jc.seniority
               FROM job_classifications jc
               JOIN posts p ON p.post_id = jc.post_id
               WHERE jc.seniority IS NOT NULL"""
        )
        work_modes = _distinct(
            """SELECT DISTINCT jc.work_mode
               FROM job_classifications jc
               JOIN posts p ON p.post_id = jc.post_id
               WHERE jc.work_mode IS NOT NULL"""
        )
        industry_verticals = _distinct(
            """SELECT DISTINCT jc.industry_vertical
               FROM job_classifications jc
               JOIN posts p ON p.post_id = jc.post_id
               WHERE jc.industry_vertical IS NOT NULL"""
        )
        company_stages = _distinct(
            """SELECT DISTINCT jc.company_stage
               FROM job_classifications jc
               JOIN posts p ON p.post_id = jc.post_id
               WHERE jc.company_stage IS NOT NULL"""
        )
        tech_stack = _distinct("SELECT DISTINCT technology FROM tech_stack")
        subreddits = _distinct("SELECT DISTINCT subreddit FROM posts")
    finally:
        conn.close()

    return FilterOptions(
        domains=domains,
        job_types=job_types,
        seniorities=seniorities,
        work_modes=work_modes,
        tech_stack=tech_stack,
        subreddits=subreddits,
        industry_verticals=industry_verticals,
        company_stages=company_stages,
    )


@st.cache_data(ttl=300)
def load_latest_scrape_timestamp() -> datetime | None:
    """Return the most recent scrape timestamp."""
    rows = execute_query("SELECT MAX(scraped_at) as latest FROM posts", fetch=True)
    if not rows:
        return None
    latest = rows[0]["latest"] if isinstance(rows[0], dict) else rows[0][0]
    if isinstance(latest, datetime):
        return latest
    if isinstance(latest, str):
        return datetime.fromisoformat(latest)
    return None


@st.cache_data(ttl=300)
def load_jobs_count(filters: FilterState) -> int:
    """Return the total number of filtered jobs."""
    where_sql, params = _build_where(filters)
    rows = execute_query(
        f"""SELECT COUNT(*) AS cnt
+            FROM posts p
+            JOIN job_classifications jc ON p.post_id = jc.post_id
+            WHERE {where_sql}""",
        tuple(params),
        fetch=True,
    )
    return int(rows[0]["cnt"] if isinstance(rows[0], dict) else rows[0][0])


@st.cache_data(ttl=300)
def load_jobs_page(filters: FilterState, page: int, page_size: int = 20) -> pd.DataFrame:
    """Return a paginated dataframe of job posts."""
    where_sql, params = _build_where(filters)
    offset = (page - 1) * page_size
    ph = _placeholder()
    query = (
        "SELECT p.post_id, p.title, p.body, p.subreddit, p.score, p.num_comments, "
        "p.created_utc, p.post_url, p.scraped_at, "
        "jc.job_type, jc.seniority, jc.domain, jc.work_mode, jc.urgency_score, jc.confidence, "
        "jc.industry_vertical, jc.company_stage, jc.compensation_min, jc.compensation_max, "
        "jc.compensation_currency, jc.compensation_period, jc.equity_mentioned, jc.is_scam, "
        "jc.post_category "
        "FROM posts p "
        "JOIN job_classifications jc ON p.post_id = jc.post_id "
        f"WHERE {where_sql} "
        "ORDER BY p.created_utc DESC "
        f"LIMIT {ph} OFFSET {ph}"
    )
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn, params=tuple(params + [page_size, offset]))
    finally:
        conn.close()

    if not df.empty:
        df["created_utc"] = pd.to_datetime(df["created_utc"], utc=True)
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
    return df


@st.cache_data(ttl=300)
def load_job_tech(post_ids: tuple[str, ...]) -> dict[str, list[str]]:
    """Return tech stack entries for the current page of posts."""
    if not post_ids:
        return {}

    ph = _placeholder()
    placeholders = ",".join([ph] * len(post_ids))
    rows = execute_query(
        f"SELECT post_id, technology FROM tech_stack WHERE post_id IN ({placeholders})",
        tuple(post_ids),
        fetch=True,
    )

    tech_map: dict[str, list[str]] = {}
    for row in rows:
        post_id = row["post_id"] if isinstance(row, dict) else row[0]
        tech = row["technology"] if isinstance(row, dict) else row[1]
        tech_map.setdefault(post_id, []).append(tech)

    return tech_map


@st.cache_data(ttl=300)
def load_kpis(filters: FilterState) -> dict[str, int | str]:
    """Return KPI values based on the current filters."""
    where_sql, params = _build_where(filters)
    rows = execute_query(
        f"""SELECT COUNT(*) AS cnt
+            FROM posts p
+            JOIN job_classifications jc ON p.post_id = jc.post_id
+            WHERE {where_sql}""",
        tuple(params),
        fetch=True,
    )
    total = int(rows[0]["cnt"] if isinstance(rows[0], dict) else rows[0][0])

    ph = _placeholder()
    rows = execute_query(
        f"""SELECT COUNT(*) AS cnt
+            FROM posts p
+            JOIN job_classifications jc ON p.post_id = jc.post_id
+            WHERE {where_sql} AND p.created_utc >= {ph}""",
        tuple(params + [_format_dt(datetime.now(tz=timezone.utc) - pd.Timedelta(days=1))]),
        fetch=True,
    )
    new_24h = int(rows[0]["cnt"] if isinstance(rows[0], dict) else rows[0][0])

    rows = execute_query(
        f"""SELECT COUNT(*) AS cnt
+            FROM posts p
+            JOIN job_classifications jc ON p.post_id = jc.post_id
+            WHERE {where_sql} AND jc.work_mode = {ph}""",
        tuple(params + ["Remote"]),
        fetch=True,
    )
    remote_count = int(rows[0]["cnt"] if isinstance(rows[0], dict) else rows[0][0])
    remote_pct = int(100 * remote_count / max(total, 1))

    rows = execute_query(
        f"""SELECT jc.domain, COUNT(*) AS cnt
+            FROM posts p
+            JOIN job_classifications jc ON p.post_id = jc.post_id
+            WHERE {where_sql} AND jc.domain IS NOT NULL
+            GROUP BY jc.domain
+            ORDER BY cnt DESC
+            LIMIT 1""",
        tuple(params),
        fetch=True,
    )
    top_domain = "-"
    if rows:
        top_domain = rows[0]["domain"] if isinstance(rows[0], dict) else rows[0][0]

    rows = execute_query(
        f"""SELECT COUNT(DISTINCT ts.technology) AS cnt
+            FROM tech_stack ts
+            JOIN posts p ON p.post_id = ts.post_id
+            JOIN job_classifications jc ON p.post_id = jc.post_id
+            WHERE {where_sql}""",
        tuple(params),
        fetch=True,
    )
    tech_count = int(rows[0]["cnt"] if isinstance(rows[0], dict) else rows[0][0])

    return {
        "total_jobs": total,
        "new_24h": new_24h,
        "remote_pct": remote_pct,
        "top_domain": top_domain,
        "tech_count": tech_count,
    }


@st.cache_data(ttl=300)
def load_mv_domain_volume_weekly(filters: FilterState) -> pd.DataFrame:
    """Load weekly domain volume from the materialized view."""
    ph = _placeholder()
    params: list[Any] = [filters.start_date, filters.end_date]
    where = f"week >= {ph} AND week <= {ph}"

    if filters.domains:
        placeholders = ",".join([ph] * len(filters.domains))
        where += f" AND domain IN ({placeholders})"
        params.extend(filters.domains)

    conn = get_connection()
    try:
        df = pd.read_sql_query(
            f"SELECT week, domain, post_count FROM mv_domain_volume_weekly WHERE {where}",
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()

    if not df.empty:
        df["week"] = pd.to_datetime(df["week"], utc=True)
    return df


@st.cache_data(ttl=300)
def load_mv_skill_demand_weekly(filters: FilterState) -> pd.DataFrame:
    """Load weekly skill demand from the materialized view."""
    ph = _placeholder()
    params: list[Any] = [filters.start_date, filters.end_date]
    where = f"week >= {ph} AND week <= {ph}"

    conn = get_connection()
    try:
        df = pd.read_sql_query(
            f"SELECT week, technology, mention_count, posts_count FROM mv_skill_demand_weekly WHERE {where}",
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()

    if not df.empty:
        df["week"] = pd.to_datetime(df["week"], utc=True)
    return df


@st.cache_data(ttl=300)
def load_mv_subreddit_quality() -> pd.DataFrame:
    """Load subreddit quality metrics."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT subreddit, total_posts, job_post_rate, scam_rate, last_7_days_volume FROM mv_subreddit_quality",
            conn,
        )
    finally:
        conn.close()
    return df


@st.cache_data(ttl=300)
def load_compensation_samples(filters: FilterState) -> pd.DataFrame:
    """Load compensation samples for box plots."""
    where_sql, params = _build_where(filters)
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """SELECT jc.domain, jc.seniority, jc.compensation_max
+               FROM posts p
+               JOIN job_classifications jc ON p.post_id = jc.post_id
+               WHERE """ + where_sql + " AND jc.compensation_max IS NOT NULL",
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()
    return df


@st.cache_data(ttl=300)
def load_industry_vertical_trend(filters: FilterState) -> pd.DataFrame:
    """Load industry vertical volume over time."""
    where_sql, params = _build_where(filters)
    if _is_postgres():
        week_expr = "date_trunc('week', p.created_utc)::date"
    else:
        week_expr = "date(p.created_utc, 'weekday 1', '-7 days')"

    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """SELECT """ + week_expr + """ AS week, jc.industry_vertical, COUNT(*) AS post_count
+               FROM posts p
+               JOIN job_classifications jc ON p.post_id = jc.post_id
+               WHERE """ + where_sql + " AND jc.industry_vertical IS NOT NULL
+               GROUP BY 1, 2
+               ORDER BY 1 ASC""",
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()

    if not df.empty:
        df["week"] = pd.to_datetime(df["week"], utc=True)
    return df


@st.cache_data(ttl=300)
def load_company_stage_distribution(filters: FilterState) -> pd.DataFrame:
    """Load company stage distribution."""
    where_sql, params = _build_where(filters)
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """SELECT jc.company_stage, COUNT(*) AS post_count
+               FROM posts p
+               JOIN job_classifications jc ON p.post_id = jc.post_id
+               WHERE """ + where_sql + " AND jc.company_stage IS NOT NULL
+               GROUP BY 1
+               ORDER BY post_count DESC""",
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()
    return df


@st.cache_data(ttl=300)
def load_scam_overview(filters: FilterState) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return scam counts by reason and recent flagged posts."""
    where_sql, params = _build_where(filters, jobs_only=False)
    conn = get_connection()
    try:
        scam_posts = pd.read_sql_query(
            """SELECT p.post_id, p.title, p.post_url, p.subreddit, p.created_utc, jc.scam_reasons
+               FROM posts p
+               JOIN job_classifications jc ON p.post_id = jc.post_id
+               WHERE """ + where_sql + " AND COALESCE(jc.is_scam, 0) = 1
+               ORDER BY p.created_utc DESC
+               LIMIT 50""",
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()

    reasons: dict[str, int] = {}
    for _, row in scam_posts.iterrows():
        raw = row.get("scam_reasons")
        try:
            parsed = pd.json.loads(raw) if isinstance(raw, str) else []
        except Exception:
            parsed = []
        for reason in parsed:
            reasons[reason] = reasons.get(reason, 0) + 1

    reasons_df = pd.DataFrame(
        [{"reason": k, "count": v} for k, v in sorted(reasons.items(), key=lambda x: x[1], reverse=True)]
    )

    if not scam_posts.empty:
        scam_posts["created_utc"] = pd.to_datetime(scam_posts["created_utc"], utc=True)

    return reasons_df, scam_posts


@st.cache_data(ttl=300)
def load_skill_heatmap(filters: FilterState) -> pd.DataFrame:
    """Return a pivot table for skill demand by domain."""
    where_sql, params = _build_where(filters)
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """SELECT jc.domain, ts.technology, COUNT(*) AS mention_count
+               FROM posts p
+               JOIN job_classifications jc ON p.post_id = jc.post_id
+               JOIN tech_stack ts ON p.post_id = ts.post_id
+               WHERE """ + where_sql + " AND jc.domain IS NOT NULL
+               GROUP BY 1, 2""",
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()

    if df.empty:
        return df

    top_tech = df.groupby("technology")["mention_count"].sum().nlargest(20).index
    df = df[df["technology"].isin(top_tech)]
    pivot = df.pivot_table(index="domain", columns="technology", values="mention_count", fill_value=0)
    return pivot


@st.cache_data(ttl=300)
def load_common_combinations(filters: FilterState) -> pd.DataFrame:
    """Return common tech stack combinations for filtered posts."""
    where_sql, params = _build_where(filters)
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """SELECT ts.post_id, ts.technology
+               FROM posts p
+               JOIN job_classifications jc ON p.post_id = jc.post_id
+               JOIN tech_stack ts ON p.post_id = ts.post_id
+               WHERE """ + where_sql,
            conn,
            params=tuple(params),
        )
    finally:
        conn.close()

    if df.empty:
        return df

    grouped = df.groupby("post_id")["technology"].apply(list)
    counts: dict[tuple[str, str], int] = {}
    for techs in grouped:
        unique = sorted({t for t in techs if isinstance(t, str) and t.strip()})
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair = (unique[i], unique[j])
                counts[pair] = counts.get(pair, 0) + 1

    pair_df = pd.DataFrame(
        [{"Tech A": a, "Tech B": b, "Co-occurrences": c} for (a, b), c in counts.items()]
    ).sort_values("Co-occurrences", ascending=False)

    return pair_df.head(15)
