"""KPI strip rendering."""

from __future__ import annotations

import streamlit as st

from src.dashboard.components.icons import ic


def render_kpis(kpis: dict[str, str | int]) -> None:
    """Render the KPI strip using precomputed metrics."""
    st.markdown(
        f"""<div class="kpi-strip">
            <div class="kpi">
                <div class="kpi-icon teal">{ic("briefcase", 18, "#0F766E")}</div>
                <div><div class="kpi-num">{kpis.get("total_jobs", 0):,}</div><div class="kpi-lbl">Job Posts</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon amber">{ic("zap", 18, "#F59E0B")}</div>
                <div><div class="kpi-num">{kpis.get("new_24h", 0)}</div><div class="kpi-lbl">New 24h</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon blue">{ic("globe", 18, "#2563EB")}</div>
                <div><div class="kpi-num">{kpis.get("remote_pct", 0)}%</div><div class="kpi-lbl">Remote Share</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon moss">{ic("layers", 18, "#10B981")}</div>
                <div><div class="kpi-num">{kpis.get("top_domain", "-")}</div><div class="kpi-lbl">Top Domain</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon slate">{ic("cpu", 18, "#64748B")}</div>
                <div><div class="kpi-num">{kpis.get("tech_count", 0)}</div><div class="kpi-lbl">Tech Skills</div></div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
