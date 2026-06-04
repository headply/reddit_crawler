"""Paginated jobs list + filtered KPI block."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api import queries
from src.api.filters import FilterParams, filter_params
from src.api.schemas import JobsResponse

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=JobsResponse)
def get_jobs(
    params: FilterParams = Depends(filter_params),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return queries.fetch_jobs(params, page=page, page_size=page_size)
