"""Per-subreddit signal quality table."""

from __future__ import annotations

from fastapi import APIRouter

from src.api import queries
from src.api.schemas import SubredditHealthResponse

router = APIRouter(tags=["subreddit-health"])


@router.get("/subreddit-health", response_model=SubredditHealthResponse)
def get_subreddit_health() -> dict:
    return queries.fetch_subreddit_health()
