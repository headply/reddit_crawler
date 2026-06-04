"""Facet values for the sidebar filters."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from src.api import queries
from src.api.schemas import FiltersResponse

router = APIRouter(tags=["filters"])

_CACHE: dict[str, Any] = {"at": 0.0, "value": None}
_TTL_SECONDS = 300


@router.get("/filters", response_model=FiltersResponse)
def get_filters() -> dict:
    now = time.time()
    if _CACHE["value"] is not None and now - _CACHE["at"] < _TTL_SECONDS:
        return _CACHE["value"]
    value = queries.fetch_filter_values()
    _CACHE["value"] = value
    _CACHE["at"] = now
    return value
