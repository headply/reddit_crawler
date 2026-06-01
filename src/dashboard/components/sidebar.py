"""Sidebar filter UI."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.dashboard.components.icons import ic
from src.dashboard.utils.data_loaders import FilterOptions, FilterState


def _date_range(option: str) -> tuple[date, date]:
    today = date.today()
    if option == "Today":
        return today, today
    if option == "7 days":
        return today - timedelta(days=7), today
    if option == "30 days":
        return today - timedelta(days=30), today
    if option == "90 days":
        return today - timedelta(days=90), today
    return date(2000, 1, 1), today


def render_sidebar(options: FilterOptions) -> FilterState:
    """Render sidebar UI and return a filter state object."""
    with st.sidebar:
        st.markdown(
            f"""<div class="sb-header">
                <div class="sb-logo">{ic("briefcase", 18, "#fff")}</div>
                <div>
                    <div class="sb-brand">Job Intelligence</div>
                    <div class="sb-sub">Signal-first job radar</div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        st.caption("TIME RANGE")
        range_opt = st.pills(
            "Time Range",
            options=["Today", "7 days", "30 days", "90 days", "All time"],
            default="30 days",
            label_visibility="collapsed",
        )
        start_date, end_date = _date_range(range_opt or "30 days")

        st.caption("SEARCH")
        keyword = st.text_input("", placeholder="Title, skill, company...", label_visibility="collapsed")

        st.markdown("<hr class='sb-divider'>", unsafe_allow_html=True)
        st.caption("FILTERS")

        with st.expander("Domain", expanded=False):
            domains = st.multiselect("", options.domains, default=options.domains, label_visibility="collapsed")

        with st.expander("Job Type", expanded=False):
            job_types = st.multiselect("", options.job_types, default=options.job_types, label_visibility="collapsed")

        with st.expander("Seniority", expanded=False):
            seniorities = st.multiselect("", options.seniorities, default=options.seniorities, label_visibility="collapsed")

        with st.expander("Work Mode", expanded=False):
            work_modes = st.multiselect("", options.work_modes, default=options.work_modes, label_visibility="collapsed")

        with st.expander("Industry Vertical", expanded=False):
            industry_verticals = st.multiselect(
                "",
                options.industry_verticals,
                default=options.industry_verticals,
                label_visibility="collapsed",
            )

        with st.expander("Company Stage", expanded=False):
            company_stages = st.multiselect(
                "",
                options.company_stages,
                default=options.company_stages,
                label_visibility="collapsed",
            )

        with st.expander("Tech Stack", expanded=False):
            tech_stack = st.multiselect(
                "",
                options.tech_stack,
                default=[],
                label_visibility="collapsed",
            )

        with st.expander("Subreddit", expanded=False):
            subreddits = st.multiselect(
                "",
                options.subreddits,
                default=options.subreddits,
                label_visibility="collapsed",
            )

        st.markdown("<hr class='sb-divider'>", unsafe_allow_html=True)
        include_scam = st.checkbox("Include flagged scams", value=False)
        min_comp = st.number_input(
            "Compensation min (annual, USD)",
            min_value=0,
            max_value=1_000_000,
            value=0,
            step=10_000,
        )

        if st.button("Refresh data"):
            st.cache_data.clear()
            st.rerun()

    return FilterState(
        start_date=start_date,
        end_date=end_date,
        keyword=keyword.strip(),
        domains=tuple(domains),
        job_types=tuple(job_types),
        seniorities=tuple(seniorities),
        work_modes=tuple(work_modes),
        tech_stack=tuple(tech_stack),
        subreddits=tuple(subreddits),
        industry_verticals=tuple(industry_verticals),
        company_stages=tuple(company_stages),
        min_compensation=min_comp if min_comp > 0 else None,
        include_scam=include_scam,
    )
