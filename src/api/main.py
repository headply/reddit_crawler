"""FastAPI app — serves the Reddit Job Intelligence dashboard.

Runs as a single uvicorn process:
  * JSON API mounted under ``/api/*``
  * Static frontend assets under ``/assets/*``
  * SPA fallback: any non-API GET returns ``static/index.html`` so React
    Router can take over (e.g. /analytics, /trends).

In production the frontend and API live at the same origin, so no CORS
middleware is needed. ``ENV=development`` enables permissive CORS for the
Vite dev server on :5173.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routers import (
    analytics,
    filters,
    jobs,
    meta,
    subreddit_health,
    tech_trends,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(os.getenv("DASHBOARD_STATIC_DIR", "static")).resolve()

app = FastAPI(
    title="Reddit Job Intelligence API",
    version="1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

if os.getenv("ENV", "").lower() == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

# ── API routers — MUST be registered before the SPA fallback ──────────────
for r in (meta.router, filters.router, jobs.router, analytics.router,
          tech_trends.router, subreddit_health.router):
    app.include_router(r, prefix="/api")


# ── Static assets ─────────────────────────────────────────────────────────
_assets_dir = STATIC_DIR / "assets"
if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
else:
    logger.warning(
        "Static assets directory %s not found; frontend will 404 until built.",
        _assets_dir,
    )


# ── SPA fallback ──────────────────────────────────────────────────────────
@app.get("/{path:path}")
def spa_fallback(path: str):
    """Return the React app for any unmatched GET so client-side routing works."""
    if path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    index = STATIC_DIR / "index.html"
    if not index.exists():
        return JSONResponse(
            {
                "detail": (
                    "Frontend not built. Run `npm run build` in /frontend "
                    "or rebuild the dashboard Docker image."
                )
            },
            status_code=503,
        )
    return FileResponse(index)
