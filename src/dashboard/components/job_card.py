"""Job card rendering."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from src.dashboard.components.icons import ic
from src.dashboard.utils.formatting import ago, format_compensation


def _badge(text: str, cls: str) -> str:
    return f"<span class='b {cls}'>{html.escape(text)}</span>"


def render_job_card(row: dict[str, Any], techs: list[str]) -> None:
    """Render a single job card."""
    title = html.escape(str(row.get("title", "")))
    post_url = row.get("post_url", "#")
    subreddit = html.escape(str(row.get("subreddit", "")))

    domain = row.get("domain")
    work_mode = row.get("work_mode")
    seniority = row.get("seniority")
    job_type = row.get("job_type")
    post_category = row.get("post_category")
    is_scam = bool(row.get("is_scam"))

    badges = ""
    if isinstance(domain, str):
        badges += _badge(domain, "b-domain")
    if isinstance(work_mode, str):
        mode_key = work_mode.lower().replace("-", "").replace(" ", "")
        badges += _badge(work_mode, f"b-{mode_key}")
    if isinstance(seniority, str):
        badges += _badge(seniority, "b-seniority")
    if isinstance(job_type, str):
        badges += _badge(job_type, "b-type")
    if isinstance(post_category, str) and post_category not in {"hiring", "for_hire", "gig_freelance"}:
        badges += _badge(post_category.replace("_", " "), "b-muted")
    if is_scam:
        badges += _badge("scam", "b-scam")

    comp_badge = format_compensation(
        row.get("compensation_min"),
        row.get("compensation_max"),
        row.get("compensation_currency"),
        row.get("compensation_period"),
    )
    if comp_badge:
        badges += _badge(comp_badge, "b-comp")

    body = row.get("body") or ""
    excerpt = html.escape(body.strip())[:260]
    if len(body.strip()) > 260:
        excerpt += "…"

    posted = ago(row.get("created_utc"))

    tech_html = "".join(
        f"<span class='tpill'>{html.escape(t)}</span>" for t in techs[:10]
    )

    st.markdown(
        f"""<div class="jcard">
            <div class="jcard-row1">
                <a class="jcard-title" href="{post_url}" target="_blank">{title}</a>
                <span class="jcard-ext">{ic("arrow-up-right", 14, "#64748B")}</span>
            </div>
            <div class="jcard-badges">{badges}</div>
            <div class="jcard-meta">
                <span class="jcard-meta-item">{ic("users", 12, "#94A3B8")} r/{subreddit}</span>
                <span class="jcard-meta-item">{ic("thumbs-up", 12, "#94A3B8")} {int(row.get("score", 0))}</span>
                <span class="jcard-meta-item">{ic("message", 12, "#94A3B8")} {int(row.get("num_comments", 0))}</span>
                <span class="jcard-meta-item">{ic("clock", 12, "#94A3B8")} {posted}</span>
            </div>
            {"<div class='jcard-excerpt'>" + excerpt + "</div>" if excerpt else ""}
            {"<div class='jcard-techs'>" + tech_html + "</div>" if tech_html else ""}
        </div>""",
        unsafe_allow_html=True,
    )
