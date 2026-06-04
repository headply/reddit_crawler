"""Tech trends — weekly demand, heatmap, top pairs."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api import queries
from src.api.filters import FilterParams, filter_params
from src.api.schemas import TechTrendsResponse

router = APIRouter(tags=["tech-trends"])


@router.get("/tech-trends", response_model=TechTrendsResponse)
def get_tech_trends(params: FilterParams = Depends(filter_params)) -> dict:
    return queries.fetch_tech_trends(params)
