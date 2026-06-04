"""Top-bar / global meta endpoint."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from src.api import queries
from src.api.schemas import MetaResponse

router = APIRouter(tags=["meta"])

_CACHE: dict[str, Any] = {"at": 0.0, "value": None}
_TTL_SECONDS = 60


@router.get("/meta", response_model=MetaResponse)
def get_meta() -> dict:
    now = time.time()
    if _CACHE["value"] is not None and now - _CACHE["at"] < _TTL_SECONDS:
        return _CACHE["value"]
    value = queries.fetch_meta()
    _CACHE["value"] = value
    _CACHE["at"] = now
    return value


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
