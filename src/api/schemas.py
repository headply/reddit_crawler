"""Pydantic v2 response models for the dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MetaResponse(BaseModel):
    total_jobs: int
    total_posts: int
    latest_scraped_at: Optional[datetime]
    latest_classified_at: Optional[datetime]
    llm_classified_pct: float
    scams_flagged: int


class FiltersResponse(BaseModel):
    domains: list[str]
    job_types: list[str]
    seniorities: list[str]
    work_modes: list[str]
    techs: list[str]
    subreddits: list[str]


class Kpis(BaseModel):
    total_jobs: int
    new_24h: int
    remote_pct: int
    top_domain: Optional[str]
    tech_skills: int


class Job(BaseModel):
    post_id: str
    title: str
    excerpt: Optional[str]
    subreddit: str
    score: int
    num_comments: int
    created_utc: datetime
    post_url: str
    domain: Optional[str]
    seniority: Optional[str]
    work_mode: Optional[str]
    job_type: Optional[str]
    post_category: Optional[str]
    industry_vertical: Optional[str]
    company_stage: Optional[str]
    compensation_min: Optional[int]
    compensation_max: Optional[int]
    compensation_currency: Optional[str]
    compensation_period: Optional[str]
    urgency_score: Optional[float]
    confidence: Optional[float]
    llm_classified: Optional[bool]
    is_scam: Optional[bool]
    tech_stack: list[str]


class JobsResponse(BaseModel):
    items: list[Job]
    total: int
    page: int
    page_size: int
    pages: int
    kpis: Kpis


class LabelValue(BaseModel):
    label: str
    value: float


class DateValue(BaseModel):
    date: str
    value: int


class SalaryBox(BaseModel):
    domain: str
    seniority: str
    median: int
    p25: int
    p75: int
    sample_size: int


class AnalyticsResponse(BaseModel):
    volume_over_time: list[DateValue]
    top_subreddits: list[LabelValue]
    domain_breakdown: list[LabelValue]
    work_mode_split: list[LabelValue]
    seniority_breakdown: list[LabelValue]
    job_type_breakdown: list[LabelValue]
    top_skills: list[LabelValue]
    salary_by_role: list[SalaryBox]


class WeeklyDemandPoint(BaseModel):
    week: str
    tech: str
    count: int


class Heatmap(BaseModel):
    domains: list[str]
    techs: list[str]
    matrix: list[list[int]]


class TechPair(BaseModel):
    a: str
    b: str
    count: int


class TechTrendsResponse(BaseModel):
    weekly_demand: list[WeeklyDemandPoint]
    heatmap: Heatmap
    pairs: list[TechPair]


class SubredditHealth(BaseModel):
    subreddit: str
    posts_scraped: int
    jobs_found: int
    scams_flagged: int
    dedup_rate: Optional[float]
    last_scraped: Optional[datetime]
    job_rate: Optional[float]


class SubredditHealthResponse(BaseModel):
    items: list[SubredditHealth]
    as_of: datetime
