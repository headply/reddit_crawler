"""Reddit Job Intelligence -- Streamlit Dashboard."""

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.db import get_connection, init_db

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Job Intelligence",
    page_icon="https://cdn-icons-png.flaticon.com/512/3281/3281289.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Icon library (Lucide outline SVG, 16 px default) ──────────────────────
_I = {
    "briefcase":    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>',
    "zap":          '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "globe":        '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    "layers":       '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    "cpu":          '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
    "arrow-up-right":'<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>',
    "thumbs-up":    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/><path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>',
    "message":      '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "clock":        '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "search":       '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "sliders":      '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>',
    "calendar":     '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    "tag":          '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
    "trending-up":  '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "bar-chart":    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "refresh":      '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
    "map-pin":      '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "users":        '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="{s}" height="{s}"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
}

def ic(name: str, size: int = 16, color: str = "currentColor") -> str:
    return _I.get(name, "").format(s=size, c=color)


# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Reset ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── Layout ── */
[data-testid="stAppViewContainer"] > .main { background: #F1F5F9; }
.main .block-container { padding: 0 2rem 2rem !important; max-width: 100% !important; }

/* ── Top bar ── */
.topbar {
    background: #fff;
    border-bottom: 1px solid #E2E8F0;
    padding: 0.9rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
    margin-left: -2rem;
    margin-right: -2rem;
}
.topbar-left { display: flex; align-items: center; gap: 0.75rem; }
.topbar-logo {
    width: 32px; height: 32px;
    background: #1E3A5F;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
}
.topbar-title { font-size: 0.95rem; font-weight: 700; color: #0F172A; letter-spacing: -0.01em; }
.topbar-sub { font-size: 0.72rem; color: #94A3B8; margin-top: 1px; }
.topbar-right { font-size: 0.72rem; color: #94A3B8; }

/* ── Content wrapper ── */
.content-wrap { padding: 1.5rem 2rem 2rem; }

/* ── KPI strip ── */
.kpi-strip {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.875rem;
    margin-bottom: 1.5rem;
}
.kpi {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.875rem;
}
.kpi-icon {
    width: 38px; height: 38px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.kpi-icon.blue   { background: #EFF6FF; }
.kpi-icon.green  { background: #ECFDF5; }
.kpi-icon.amber  { background: #FFFBEB; }
.kpi-icon.violet { background: #F5F3FF; }
.kpi-icon.slate  { background: #F1F5F9; }
.kpi-num { font-size: 1.45rem; font-weight: 700; color: #0F172A; line-height: 1; }
.kpi-lbl { font-size: 0.7rem; color: #94A3B8; font-weight: 500; margin-top: 3px; }

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid #E2E8F0 !important;
    gap: 0 !important;
    padding: 0 !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 0.65rem 1.25rem !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: #64748B !important;
    margin-bottom: -1px !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    border-bottom-color: #2563EB !important;
    color: #2563EB !important;
    font-weight: 600 !important;
}
[data-baseweb="tab-panel"] { padding: 1.25rem 0 0 !important; }

/* ── Job card ── */
.jcard {
    background: #fff;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.12s, box-shadow 0.12s;
}
.jcard:hover {
    border-color: #93C5FD;
    box-shadow: 0 2px 16px rgba(37,99,235,0.07);
}
.jcard-row1 { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.45rem; }
.jcard-title { font-size: 0.92rem; font-weight: 600; color: #0F172A; text-decoration: none; line-height: 1.35; }
.jcard-title:hover { color: #2563EB; }
.jcard-ext { flex-shrink: 0; opacity: 0.35; margin-top: 2px; }
.jcard-badges { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-bottom: 0.55rem; }

/* Badges */
.b {
    display: inline-flex; align-items: center;
    padding: 2px 8px; border-radius: 4px;
    font-size: 0.67rem; font-weight: 600; letter-spacing: 0.01em;
    white-space: nowrap;
}
.b-domain   { background: #EFF6FF; color: #1D4ED8; }
.b-remote   { background: #ECFDF5; color: #065F46; }
.b-hybrid   { background: #FFFBEB; color: #92400E; }
.b-onsite   { background: #FEF2F2; color: #991B1B; }
.b-junior   { background: #F0FDF4; color: #166534; }
.b-mid      { background: #F0F9FF; color: #075985; }
.b-senior   { background: #F5F3FF; color: #5B21B6; }
.b-lead     { background: #FFF7ED; color: #9A3412; }
.b-type     { background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; }

/* Meta row */
.jcard-meta {
    display: flex; align-items: center;
    flex-wrap: wrap; gap: 0.9rem;
    font-size: 0.7rem; color: #94A3B8;
    margin-bottom: 0.55rem;
}
.jcard-meta-item { display: inline-flex; align-items: center; gap: 0.25rem; }
.jcard-meta-item svg { flex-shrink: 0; }

/* Excerpt */
.jcard-excerpt { font-size: 0.78rem; color: #64748B; line-height: 1.6; margin-bottom: 0.55rem; }

/* Tech pills */
.jcard-techs { display: flex; flex-wrap: wrap; gap: 0.25rem; }
.tpill {
    background: #F8FAFC; color: #475569;
    border: 1px solid #E2E8F0;
    padding: 1px 7px; border-radius: 4px;
    font-size: 0.65rem;
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}

/* ── Section heading ── */
.sec-head {
    font-size: 0.68rem; font-weight: 700;
    letter-spacing: 0.07em; text-transform: uppercase;
    color: #64748B; margin-bottom: 0.875rem;
    padding-bottom: 0.5rem; border-bottom: 1px solid #F1F5F9;
}

/* ── Pagination ── */
.pg-bar {
    display: flex; align-items: center;
    justify-content: space-between;
    padding: 0.875rem 0 0;
    border-top: 1px solid #F1F5F9;
    margin-top: 0.25rem;
}
.pg-info { font-size: 0.72rem; color: #94A3B8; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #fff !important;
    border-right: 1px solid #E2E8F0;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
.sb-header {
    padding: 1.25rem 1.1rem 1rem;
    border-bottom: 1px solid #F1F5F9;
}
.sb-brand { font-size: 0.85rem; font-weight: 700; color: #0F172A; letter-spacing: -0.01em; }
.sb-sub   { font-size: 0.68rem; color: #94A3B8; margin-top: 2px; }
.sb-section {
    padding: 0.875rem 1.1rem 0;
}
.sb-label {
    font-size: 0.62rem; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: #94A3B8; margin-bottom: 0.4rem;
    display: flex; align-items: center; gap: 0.3rem;
}
.sb-divider { border: none; border-top: 1px solid #F1F5F9; margin: 0.5rem 0; }

/* Date range pills */
.date-pills { display: flex; gap: 0.35rem; flex-wrap: wrap; margin-bottom: 0.25rem; }
.dpill {
    padding: 4px 10px; border-radius: 5px;
    font-size: 0.72rem; font-weight: 500;
    cursor: pointer; border: 1px solid #E2E8F0;
    background: #fff; color: #64748B;
    transition: all 0.1s;
}
.dpill.active { background: #1E3A5F; color: #fff; border-color: #1E3A5F; }

/* Streamlit widget overrides inside sidebar */
[data-testid="stSidebar"] .stTextInput > div > div {
    border-radius: 7px !important;
    border-color: #E2E8F0 !important;
    font-size: 0.82rem !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] > div {
    border-radius: 7px !important;
    border-color: #E2E8F0 !important;
    font-size: 0.8rem !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: #EFF6FF !important;
    border: none !important;
    border-radius: 4px !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span { color: #1D4ED8 !important; font-size: 0.7rem !important; }

/* Radio as date selector */
[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    flex-direction: row !important; gap: 0.3rem !important; flex-wrap: wrap !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: #E2E8F0; border: 1.5px solid #CBD5E1;
    border-radius: 6px; padding: 5px 11px;
    font-size: 0.73rem !important; color: #1E293B !important;
    font-weight: 500 !important;
    cursor: pointer; transition: all 0.12s;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: #1E3A5F !important; color: #fff !important; border-color: #1E3A5F !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] input {
    position: absolute !important; opacity: 0 !important; pointer-events: none !important;
}

/* Expander clean-up */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border: 1px solid #F1F5F9 !important;
    border-radius: 7px !important;
    background: #FAFAFA;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    font-size: 0.75rem !important; font-weight: 600 !important; color: #64748B !important;
}

/* Streamlit button */
[data-testid="stSidebar"] .stButton button {
    width: 100%; border-radius: 7px;
    background: #F1F5F9; border: 1px solid #E2E8F0;
    color: #475569; font-size: 0.78rem;
    font-weight: 500; padding: 0.45rem 0.75rem;
    display: flex; align-items: center; justify-content: center; gap: 0.3rem;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: #E2E8F0; color: #1E293B;
}

/* Chart container */
.chart-wrap {
    background: #fff; border: 1px solid #E2E8F0;
    border-radius: 10px; padding: 1.25rem;
    margin-bottom: 0.875rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────
def _ago(dt: pd.Timestamp) -> str:
    now = pd.Timestamp.now(tz="UTC")
    if dt.tzinfo is None:
        dt = dt.tz_localize("UTC")
    d = (now - dt).days
    s = (now - dt).seconds
    if d == 0:
        h = s // 3600
        return "just now" if h == 0 else f"{h}h ago"
    if d == 1:
        return "1d ago"
    if d < 30:
        return f"{d}d ago"
    if d < 365:
        return f"{d // 30}mo ago"
    return f"{d // 365}y ago"


def _badge(text: str, cls: str) -> str:
    return f'<span class="b {cls}">{text}</span>'


def _mode_badge(v) -> str:
    if not isinstance(v, str):
        return ""
    return _badge(v, {"Remote": "b-remote", "Hybrid": "b-hybrid", "On-site": "b-onsite"}.get(v, "b-domain"))


def _sen_badge(v) -> str:
    if not isinstance(v, str):
        return ""
    return _badge(v, {"Junior": "b-junior", "Mid": "b-mid", "Senior": "b-senior", "Lead/Principal": "b-lead"}.get(v, "b-mid"))


def _type_badge(v) -> str:
    return _badge(v, "b-type") if isinstance(v, str) else ""


# ── Chart defaults ─────────────────────────────────────────────────────────
_FONT = dict(family="Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif", size=12, color="#374151")
_MARGIN = dict(l=4, r=4, t=28, b=4)
_COLORS = ["#1E3A5F", "#2563EB", "#0EA5E9", "#06B6D4", "#10B981", "#8B5CF6", "#F59E0B", "#EF4444"]

def _base_layout(**kw):
    return dict(
        plot_bgcolor="white", paper_bgcolor="white",
        font=_FONT, margin=_MARGIN,
        xaxis=dict(showgrid=True, gridcolor="#F1F5F9", linecolor="#E2E8F0", tickcolor="rgba(0,0,0,0)"),
        yaxis=dict(showgrid=True, gridcolor="#F1F5F9", linecolor="#E2E8F0", tickcolor="rgba(0,0,0,0)"),
        showlegend=False,
        **kw,
    )


# ── Data ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    init_db()
    try:
        conn = get_connection()
    except (ConnectionError, ImportError, OSError) as exc:
        raise ConnectionError(str(exc)) from exc
    try:
        jobs = pd.read_sql_query(
            """SELECT p.post_id, p.title, p.body, p.subreddit,
                      p.score, p.num_comments, p.created_utc, p.post_url,
                      jc.is_job, jc.job_type, jc.seniority, jc.domain,
                      jc.work_mode, jc.urgency_score, jc.confidence, jc.llm_classified
               FROM posts p
               LEFT JOIN job_classifications jc ON p.post_id = jc.post_id""",
            conn,
        )
        tech = pd.read_sql_query("SELECT post_id, technology FROM tech_stack", conn)
    finally:
        conn.close()

    if not jobs.empty:
        jobs["created_utc"] = pd.to_datetime(jobs["created_utc"], utc=True)
        jobs["date"] = jobs["created_utc"].dt.date
        jobs["week"] = jobs["created_utc"].dt.to_period("W").astype(str)

    return jobs, tech


# ── Sidebar ────────────────────────────────────────────────────────────────
def render_sidebar(jobs: pd.DataFrame, tech: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        # Header
        st.markdown(
            f"""<div class="sb-header">
                <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem">
                    <div class="topbar-logo">{ic("briefcase", 16, "#fff")}</div>
                    <div>
                        <div class="sb-brand">Job Intelligence</div>
                        <div class="sb-sub">Automated job intelligence</div>
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # Date range
        st.markdown(
            f'<div class="sb-section"><div class="sb-label">{ic("calendar", 11, "#94A3B8")} Time Range</div></div>',
            unsafe_allow_html=True,
        )
        with st.container():
            date_opt = st.radio(
                "", ["Today", "7 days", "30 days", "All time"],
                index=2, label_visibility="collapsed",
            )

        # Search
        st.markdown(
            f'<div class="sb-section" style="padding-top:0.75rem"><div class="sb-label">{ic("search", 11, "#94A3B8")} Search</div></div>',
            unsafe_allow_html=True,
        )
        keyword = st.text_input("", placeholder="Title, skill, company...", label_visibility="collapsed")

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        # Filters
        st.markdown(
            f'<div class="sb-section"><div class="sb-label">{ic("sliders", 11, "#94A3B8")} Filters</div></div>',
            unsafe_allow_html=True,
        )

        domains = sorted(jobs["domain"].dropna().unique())
        with st.expander("Domain"):
            sel_domain = st.multiselect("", domains, default=domains, label_visibility="collapsed",
                                        placeholder="All domains")

        types = sorted(jobs["job_type"].dropna().unique())
        with st.expander("Job Type"):
            sel_type = st.multiselect("", types, default=types, label_visibility="collapsed",
                                      placeholder="All types")

        levels = sorted(jobs["seniority"].dropna().unique())
        with st.expander("Seniority"):
            sel_level = st.multiselect("", levels, default=levels, label_visibility="collapsed",
                                       placeholder="All levels")

        modes = sorted(jobs["work_mode"].dropna().unique())
        with st.expander("Work Mode"):
            sel_mode = st.multiselect("", modes, default=modes, label_visibility="collapsed",
                                      placeholder="All modes")

        all_techs = sorted(tech["technology"].unique()) if not tech.empty else []
        with st.expander("Tech Stack"):
            sel_tech = st.multiselect("", all_techs, label_visibility="collapsed",
                                      placeholder="Any technology")

        with st.expander("Subreddit"):
            subs     = sorted(jobs["subreddit"].dropna().unique())
            sel_subs = st.multiselect("", subs, default=subs, label_visibility="collapsed")

        st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

        if st.button(f"Refresh data"):
            st.cache_data.clear()
            st.rerun()

    # Apply filters
    now = pd.Timestamp.now(tz="UTC")
    cutoff = {"Today": now - timedelta(days=1), "7 days": now - timedelta(days=7),
              "30 days": now - timedelta(days=30), "All time": pd.Timestamp("2000-01-01", tz="UTC")}[date_opt]

    f = jobs[jobs["is_job"] == True].copy() if "is_job" in jobs.columns else jobs.copy()  # noqa: E712
    f = f[f["created_utc"] >= cutoff]

    if keyword.strip():
        kw = keyword.strip().lower()
        f = f[f["title"].str.lower().str.contains(kw, na=False) | f["body"].str.lower().str.contains(kw, na=False)]

    if sel_domain: f = f[f["domain"].isin(sel_domain) | f["domain"].isna()]
    if sel_type:   f = f[f["job_type"].isin(sel_type) | f["job_type"].isna()]
    if sel_level:  f = f[f["seniority"].isin(sel_level) | f["seniority"].isna()]
    if sel_mode:   f = f[f["work_mode"].isin(sel_mode) | f["work_mode"].isna()]
    if sel_tech:
        ids = tech[tech["technology"].isin(sel_tech)]["post_id"].unique()
        f = f[f["post_id"].isin(ids)]
    if sel_subs:   f = f[f["subreddit"].isin(sel_subs)]

    return f


# ── KPI strip ──────────────────────────────────────────────────────────────
def render_kpis(f: pd.DataFrame, tech: pd.DataFrame) -> None:
    now = pd.Timestamp.now(tz="UTC")
    n24 = int((f["created_utc"] >= now - timedelta(days=1)).sum()) if not f.empty else 0
    remote_pct = 0
    if not f.empty and "work_mode" in f.columns:
        remote_pct = int(100 * (f["work_mode"] == "Remote").sum() / max(len(f), 1))
    top_domain = "—"
    if not f.empty:
        vc = f["domain"].dropna().value_counts()
        if not vc.empty:
            top_domain = vc.index[0].split(" ")[0]   # first word only so it fits
    tech_n = tech[tech["post_id"].isin(f["post_id"])]["technology"].nunique() if not tech.empty and not f.empty else 0

    st.markdown(
        f"""<div class="kpi-strip">
            <div class="kpi">
                <div class="kpi-icon blue">{ic("briefcase", 18, "#2563EB")}</div>
                <div><div class="kpi-num">{len(f):,}</div><div class="kpi-lbl">Job Posts</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon green">{ic("zap", 18, "#059669")}</div>
                <div><div class="kpi-num">{n24}</div><div class="kpi-lbl">New last 24 h</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon amber">{ic("globe", 18, "#D97706")}</div>
                <div><div class="kpi-num">{remote_pct}%</div><div class="kpi-lbl">Remote</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon violet">{ic("layers", 18, "#7C3AED")}</div>
                <div><div class="kpi-num">{top_domain}</div><div class="kpi-lbl">Top Domain</div></div>
            </div>
            <div class="kpi">
                <div class="kpi-icon slate">{ic("cpu", 18, "#475569")}</div>
                <div><div class="kpi-num">{tech_n}</div><div class="kpi-lbl">Tech Skills</div></div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ── Browse Jobs ────────────────────────────────────────────────────────────
def render_browse(f: pd.DataFrame, tech: pd.DataFrame) -> None:
    if f.empty:
        st.info("No job posts match the current filters.")
        return

    df = f.sort_values("created_utc", ascending=False)
    PAGE = 20
    total = len(df)
    pages = max(1, (total + PAGE - 1) // PAGE)

    col_a, col_b = st.columns([4, 1])
    with col_a:
        st.markdown(f'<div class="pg-info">{total:,} listings found</div>', unsafe_allow_html=True)
    with col_b:
        page = int(st.number_input("", min_value=1, max_value=pages, value=1,
                                   step=1, label_visibility="collapsed"))

    slice_df = df.iloc[(page - 1) * PAGE: page * PAGE]

    for _, r in slice_df.iterrows():
        techs = tech[tech["post_id"] == r["post_id"]]["technology"].tolist() if not tech.empty else []
        badges = (
            (_badge(r["domain"], "b-domain") if pd.notna(r.get("domain")) else "")
            + _mode_badge(r.get("work_mode"))
            + _sen_badge(r.get("seniority"))
            + _type_badge(r.get("job_type"))
        )
        tech_html = "".join(f'<span class="tpill">{t}</span>' for t in techs[:12])
        body = (r.get("body") or "")
        excerpt = ""
        if isinstance(body, str) and body.strip():
            raw = body.strip().replace("<", "&lt;").replace(">", "&gt;")
            excerpt = raw[:230] + ("…" if len(raw) > 230 else "")

        posted = _ago(r["created_utc"]) if pd.notna(r.get("created_utc")) else ""

        st.markdown(
            f"""<div class="jcard">
                <div class="jcard-row1">
                    <a class="jcard-title" href="{r['post_url']}" target="_blank">{r['title'][:130]}</a>
                    <span class="jcard-ext">{ic("arrow-up-right", 14, "#64748B")}</span>
                </div>
                <div class="jcard-badges">{badges}</div>
                <div class="jcard-meta">
                    <span class="jcard-meta-item">{ic("users", 12, "#CBD5E1")} r/{r['subreddit']}</span>
                    <span class="jcard-meta-item">{ic("thumbs-up", 12, "#CBD5E1")} {int(r.get('score', 0))}</span>
                    <span class="jcard-meta-item">{ic("message", 12, "#CBD5E1")} {int(r.get('num_comments', 0))}</span>
                    <span class="jcard-meta-item">{ic("clock", 12, "#CBD5E1")} {posted}</span>
                </div>
                {"<div class='jcard-excerpt'>" + excerpt + "</div>" if excerpt else ""}
                {"<div class='jcard-techs'>" + tech_html + "</div>" if tech_html else ""}
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="pg-info" style="padding-top:0.75rem">Page {page} of {pages}</div>',
        unsafe_allow_html=True,
    )


# ── Analytics ──────────────────────────────────────────────────────────────
def render_analytics(f: pd.DataFrame, tech: pd.DataFrame) -> None:
    if f.empty:
        st.info("No data for the current filters.")
        return

    def chart_wrap(fig, height=300):
        fig.update_layout(height=height)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    r1a, r1b = st.columns(2)

    with r1a:
        st.markdown('<div class="sec-head">Job Volume Over Time</div>', unsafe_allow_html=True)
        if "date" in f.columns:
            vol = f.groupby("date").size().reset_index(name="n")
            fig = go.Figure(go.Scatter(
                x=vol["date"], y=vol["n"], mode="lines",
                line=dict(color="#2563EB", width=2.5),
                fill="tozeroy", fillcolor="rgba(37,99,235,0.07)",
            ))
            fig.update_layout(**_base_layout(xaxis_title="", yaxis_title="Posts"))
            chart_wrap(fig)

    with r1b:
        st.markdown('<div class="sec-head">Top Subreddits</div>', unsafe_allow_html=True)
        subs = f["subreddit"].value_counts().head(10).reset_index()
        subs.columns = ["Subreddit", "n"]
        fig = px.bar(subs, x="n", y="Subreddit", orientation="h", color_discrete_sequence=["#2563EB"])
        fig.update_layout(**_base_layout(xaxis_title="Posts", yaxis_title="",
                                         yaxis=dict(autorange="reversed", gridcolor="#F1F5F9",
                                                    linecolor="#E2E8F0", tickcolor="rgba(0,0,0,0)")))
        chart_wrap(fig)

    r2a, r2b = st.columns(2)

    with r2a:
        st.markdown('<div class="sec-head">Domain Breakdown</div>', unsafe_allow_html=True)
        d = f["domain"].dropna().value_counts().reset_index()
        d.columns = ["Domain", "n"]
        if not d.empty:
            fig = px.pie(d, values="n", names="Domain", hole=0.52,
                         color_discrete_sequence=_COLORS)
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white", font=_FONT,
                margin=dict(l=4, r=4, t=4, b=4), showlegend=True,
                legend=dict(font=dict(size=11), orientation="v"),
            )
            fig.update_traces(textposition="none")
            chart_wrap(fig, 300)

    with r2b:
        st.markdown('<div class="sec-head">Work Mode Split</div>', unsafe_allow_html=True)
        m = f["work_mode"].dropna().value_counts().reset_index()
        m.columns = ["Mode", "n"]
        if not m.empty:
            cmap = {"Remote": "#059669", "Hybrid": "#D97706", "On-site": "#DC2626"}
            fig = px.pie(m, values="n", names="Mode", hole=0.52,
                         color="Mode", color_discrete_map=cmap)
            fig.update_layout(
                plot_bgcolor="white", paper_bgcolor="white", font=_FONT,
                margin=dict(l=4, r=4, t=4, b=4), showlegend=True,
                legend=dict(font=dict(size=11)),
            )
            fig.update_traces(textposition="none")
            chart_wrap(fig, 300)

    r3a, r3b = st.columns(2)

    with r3a:
        st.markdown('<div class="sec-head">Seniority Breakdown</div>', unsafe_allow_html=True)
        order = ["Junior", "Mid", "Senior", "Lead/Principal"]
        s = f["seniority"].dropna().value_counts().reindex(order).dropna().reset_index()
        s.columns = ["Level", "n"]
        if not s.empty:
            fig = px.bar(s, x="Level", y="n",
                         color="Level",
                         color_discrete_sequence=["#059669", "#2563EB", "#7C3AED", "#D97706"])
            fig.update_layout(**_base_layout(xaxis_title="", yaxis_title="Posts", showlegend=False))
            chart_wrap(fig, 280)

    with r3b:
        st.markdown('<div class="sec-head">Job Type Breakdown</div>', unsafe_allow_html=True)
        t = f["job_type"].dropna().value_counts().reset_index()
        t.columns = ["Type", "n"]
        if not t.empty:
            fig = px.bar(t, x="n", y="Type", orientation="h", color_discrete_sequence=["#0EA5E9"])
            fig.update_layout(**_base_layout(xaxis_title="Posts", yaxis_title="",
                                             yaxis=dict(autorange="reversed", gridcolor="#F1F5F9",
                                                        linecolor="#E2E8F0", tickcolor="rgba(0,0,0,0)")))
            chart_wrap(fig, 280)

    st.markdown('<div class="sec-head" style="margin-top:1rem">Top 20 In-Demand Skills</div>', unsafe_allow_html=True)
    if not tech.empty:
        rt = tech[tech["post_id"].isin(f["post_id"])]
        sk = rt["technology"].value_counts().head(20).reset_index()
        sk.columns = ["Technology", "n"]
        fig = px.bar(sk, x="n", y="Technology", orientation="h",
                     color="n", color_continuous_scale=["#DBEAFE", "#1E3A5F"])
        fig.update_layout(
            **_base_layout(xaxis_title="Mentions", yaxis_title="",
                           yaxis=dict(autorange="reversed", gridcolor="#F1F5F9",
                                      linecolor="#E2E8F0", tickcolor="rgba(0,0,0,0)")),
            height=520, coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Tech Trends ────────────────────────────────────────────────────────────
def render_tech_trends(f: pd.DataFrame, tech: pd.DataFrame) -> None:
    if f.empty or tech.empty:
        st.info("Not enough data.")
        return

    rt = tech[tech["post_id"].isin(f["post_id"])]
    if rt.empty:
        st.info("No tech stack data for current filters.")
        return

    top8 = rt["technology"].value_counts().head(8).index.tolist()
    merged = rt.merge(f[["post_id", "week"]], on="post_id", how="left")
    merged = merged[merged["technology"].isin(top8)]
    weekly = merged.groupby(["week", "technology"]).size().reset_index(name="n")

    st.markdown('<div class="sec-head">Weekly Demand — Top 8 Technologies</div>', unsafe_allow_html=True)
    if not weekly.empty:
        fig = px.line(weekly, x="week", y="n", color="technology",
                      markers=True, color_discrete_sequence=_COLORS)
        fig.update_layout(
            **_base_layout(xaxis_title="Week", yaxis_title="Mentions",
                           showlegend=True,
                           legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                       xanchor="left", x=0, font=dict(size=11))),
            height=360,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="sec-head" style="margin-top:1.25rem">Tech Skills by Domain (Heatmap)</div>',
                unsafe_allow_html=True)
    dt = rt.merge(f[["post_id", "domain"]], on="post_id", how="left").dropna(subset=["domain"])
    top20 = rt["technology"].value_counts().head(20).index.tolist()
    dt = dt[dt["technology"].isin(top20)]
    if not dt.empty:
        pivot = (dt.groupby(["domain", "technology"]).size()
                 .reset_index(name="n")
                 .pivot(index="domain", columns="technology", values="n")
                 .fillna(0))
        fig = px.imshow(pivot, color_continuous_scale=["#F8FAFC", "#1E3A5F"],
                        aspect="auto", text_auto=True)
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white", font=_FONT,
            margin=dict(l=4, r=4, t=4, b=4),
            coloraxis_showscale=False, xaxis_title="", yaxis_title="",
            height=400,
        )
        fig.update_traces(textfont_size=10)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="sec-head" style="margin-top:1.25rem">Common Tech Combinations</div>',
                unsafe_allow_html=True)
    pt = rt.groupby("post_id")["technology"].apply(list)
    pairs: dict[tuple, int] = {}
    for ts in pt:
        ts = sorted(set(ts))
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                k = (ts[i], ts[j])
                pairs[k] = pairs.get(k, 0) + 1
    if pairs:
        pair_df = (pd.DataFrame([{"Tech A": a, "Tech B": b, "Co-occurrences": c}
                                  for (a, b), c in pairs.items()])
                   .sort_values("Co-occurrences", ascending=False).head(15))
        st.dataframe(pair_df, hide_index=True, use_container_width=True)


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> None:
    try:
        jobs, tech = load_data()
    except ConnectionError as exc:
        st.error(f"Database connection failed: {exc}")
        return

    if jobs.empty:
        st.info("No data yet. Run the pipeline first:\n\n```bash\npython -m src.pipeline.run\n```")
        return

    filtered = render_sidebar(jobs, tech)

    # Top bar
    total_db = int((jobs["is_job"] == True).sum()) if "is_job" in jobs.columns else len(jobs)  # noqa: E712
    latest = jobs["created_utc"].max()
    latest_str = _ago(latest) if pd.notna(latest) else "unknown"
    st.markdown(
        f"""<div class="topbar">
            <div class="topbar-left">
                <div class="topbar-logo">{ic("briefcase", 16, "#fff")}</div>
                <div>
                    <div class="topbar-title">Job Intelligence</div>
                    <div class="topbar-sub">Daily job listings from Reddit communities</div>
                </div>
            </div>
            <div class="topbar-right">
                {total_db:,} jobs in database &nbsp;·&nbsp; last updated {latest_str}
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    render_kpis(filtered, tech)

    tab1, tab2, tab3 = st.tabs(["Browse Jobs", "Analytics", "Tech Trends"])

    with tab1:
        render_browse(filtered, tech)
    with tab2:
        render_analytics(filtered, tech)
    with tab3:
        render_tech_trends(filtered, tech)


if __name__ == "__main__":
    main()
