"""Charts endpoint — all analytics data in one response."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api import queries
from src.api.filters import FilterParams, filter_params
from src.api.schemas import AnalyticsResponse

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(params: FilterParams = Depends(filter_params)) -> dict:
    return queries.fetch_analytics(params)
