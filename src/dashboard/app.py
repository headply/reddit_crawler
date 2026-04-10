"""Reddit Job Intelligence -- Streamlit Dashboard.

Three-tab layout:
  Browse Jobs  -- filterable job cards
  Analytics    -- charts and breakdowns
  Tech Trends  -- technology demand over time
"""

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.db import get_connection, init_db

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Reddit Job Intelligence",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] { background: #F4F6FB; }
.main .block-container { padding-top: 1.2rem; max-width: 1280px; }

.kpi-row { display: flex; gap: 1rem; margin-bottom: 1.4rem; flex-wrap: wrap; }
.kpi-card {
    flex: 1; min-width: 140px;
    background: white;
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    border-top: 4px solid #6C63FF;
}
.kpi-card.green  { border-top-color: #10B981; }
.kpi-card.orange { border-top-color: #F59E0B; }
.kpi-card.pink   { border-top-color: #EC4899; }
.kpi-card.teal   { border-top-color: #0EA5E9; }
.kpi-value { font-size: 2rem; font-weight: 700; color: #1E1B4B; line-height: 1; }
.kpi-label { font-size: 0.78rem; color: #6B7280; margin-top: 0.35rem; }

.job-card {
    background: white;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.9rem;
    border-left: 4px solid #6C63FF;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.15s;
}
.job-card:hover { box-shadow: 0 4px 18px rgba(108,99,255,0.13); }
.job-card-title { font-size: 0.98rem; font-weight: 600; margin-bottom: 0.4rem; }
.job-card-title a { color: #1E1B4B; text-decoration: none; }
.job-card-title a:hover { color: #6C63FF; }
.job-meta { font-size: 0.73rem; color: #9CA3AF; margin: 0.35rem 0; }
.job-excerpt { font-size: 0.8rem; color: #6B7280; margin: 0.4rem 0; line-height: 1.5; }

.badge {
    display: inline-block; border-radius: 20px;
    padding: 2px 9px; font-size: 0.69rem; font-weight: 600;
    margin-right: 4px; margin-bottom: 3px;
}
.b-domain    { background:#EEF2FF; color:#6C63FF; }
.b-remote    { background:#ECFDF5; color:#059669; }
.b-hybrid    { background:#FFF7ED; color:#D97706; }
.b-onsite    { background:#FEF2F2; color:#DC2626; }
.b-junior    { background:#F0FDF4; color:#16A34A; }
.b-mid       { background:#EFF6FF; color:#2563EB; }
.b-senior    { background:#FDF4FF; color:#9333EA; }
.b-lead      { background:#FEF3C7; color:#92400E; }
.b-fulltime  { background:#EDE9FE; color:#7C3AED; }
.b-contract  { background:#FFF7ED; color:#C2410C; }
.b-freelance { background:#FFF1F2; color:#BE185D; }
.b-internship{ background:#ECFDF5; color:#047857; }
.b-parttime  { background:#F3F4F6; color:#374151; }

.tech-tag {
    display: inline-block;
    background: #F1F5F9; color: #475569;
    border-radius: 5px; padding: 1px 7px;
    font-size: 0.67rem; font-family: monospace;
    margin: 2px;
}

.section-title {
    font-size: 1.15rem; font-weight: 700;
    color: #1E1B4B; margin-bottom: 0.8rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #E0E7FF;
}

[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E5E7EB; }
[data-baseweb="tab-list"] { gap: 6px; }
[data-baseweb="tab"] { border-radius: 8px 8px 0 0 !important; font-weight: 600 !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _time_ago(dt: pd.Timestamp) -> str:
    now = pd.Timestamp.now(tz="UTC")
    if dt.tzinfo is None:
        dt = dt.tz_localize("UTC")
    diff = now - dt
    days = diff.days
    if days == 0:
        hours = diff.seconds // 3600
        return "just now" if hours == 0 else f"{hours}h ago"
    if days == 1:
        return "1 day ago"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def _badge(text: str, css_class: str) -> str:
    return f'<span class="badge {css_class}">{text}</span>'


def _work_mode_badge(mode) -> str:
    if not mode or not isinstance(mode, str):
        return ""
    cls = {"Remote": "b-remote", "Hybrid": "b-hybrid", "On-site": "b-onsite"}.get(mode, "b-domain")
    return _badge(mode, cls)


def _seniority_badge(level) -> str:
    if not level or not isinstance(level, str):
        return ""
    cls = {"Junior": "b-junior", "Mid": "b-mid", "Senior": "b-senior", "Lead/Principal": "b-lead"}.get(level, "b-mid")
    return _badge(level, cls)


def _job_type_badge(jtype) -> str:
    if not jtype or not isinstance(jtype, str):
        return ""
    cls = {
        "Full-time": "b-fulltime", "Contract": "b-contract",
        "Freelance": "b-freelance", "Internship": "b-internship", "Part-time": "b-parttime",
    }.get(jtype, "b-fulltime")
    return _badge(jtype, cls)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    init_db()
    try:
        conn = get_connection()
    except (ConnectionError, ImportError, OSError) as exc:
        raise ConnectionError(str(exc)) from exc

    try:
        jobs_df = pd.read_sql_query(
            """SELECT p.post_id, p.title, p.body, p.author, p.subreddit,
                      p.score, p.num_comments, p.created_utc, p.post_url,
                      jc.is_job, jc.job_type, jc.seniority, jc.domain,
                      jc.work_mode, jc.urgency_score, jc.confidence,
                      jc.llm_classified
               FROM posts p
               LEFT JOIN job_classifications jc ON p.post_id = jc.post_id""",
            conn,
        )
        tech_df = pd.read_sql_query("SELECT post_id, technology FROM tech_stack", conn)
    finally:
        conn.close()

    if not jobs_df.empty and "created_utc" in jobs_df.columns:
        jobs_df["created_utc"] = pd.to_datetime(jobs_df["created_utc"], utc=True)
        jobs_df["date"] = jobs_df["created_utc"].dt.date
        jobs_df["week"] = jobs_df["created_utc"].dt.to_period("W").astype(str)

    return jobs_df, tech_df


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar(jobs_df: pd.DataFrame, tech_df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("## 💼 Job Intelligence")
        st.markdown("---")

        st.markdown("### Date Range")
        date_opt = st.radio("", ["Today", "Last 7 days", "Last 30 days", "All time"],
                            index=2, label_visibility="collapsed")
        now_utc = pd.Timestamp.now(tz="UTC")
        cutoff = {
            "Today": now_utc - timedelta(days=1),
            "Last 7 days": now_utc - timedelta(days=7),
            "Last 30 days": now_utc - timedelta(days=30),
            "All time": pd.Timestamp("2000-01-01", tz="UTC"),
        }[date_opt]

        st.markdown("---")
        st.markdown("### Search")
        keyword = st.text_input("", placeholder="e.g. Python, Senior, Remote...", label_visibility="collapsed")

        st.markdown("---")
        st.markdown("### Filters")

        all_domains = sorted(jobs_df["domain"].dropna().unique())
        sel_domains = st.multiselect("Domain", all_domains, default=all_domains)

        all_types = sorted(jobs_df["job_type"].dropna().unique())
        sel_types = st.multiselect("Job Type", all_types, default=all_types)

        all_seniority = sorted(jobs_df["seniority"].dropna().unique())
        sel_seniority = st.multiselect("Seniority", all_seniority, default=all_seniority)

        all_modes = sorted(jobs_df["work_mode"].dropna().unique())
        sel_modes = st.multiselect("Work Mode", all_modes, default=all_modes)

        all_techs = sorted(tech_df["technology"].unique()) if not tech_df.empty else []
        sel_techs = st.multiselect("Tech Stack", all_techs)

        with st.expander("Subreddit", expanded=False):
            all_subs = sorted(jobs_df["subreddit"].dropna().unique())
            sel_subs = st.multiselect("", all_subs, default=all_subs, label_visibility="collapsed")

        st.markdown("---")
        if st.button("Refresh data"):
            st.cache_data.clear()
            st.rerun()

    # Apply filters
    f = jobs_df[jobs_df["is_job"] == True].copy() if "is_job" in jobs_df.columns else jobs_df.copy()  # noqa: E712

    if "created_utc" in f.columns:
        f = f[f["created_utc"] >= cutoff]

    if keyword.strip():
        kw = keyword.strip().lower()
        mask = (
            f["title"].str.lower().str.contains(kw, na=False)
            | f["body"].str.lower().str.contains(kw, na=False)
        )
        f = f[mask]

    if sel_domains:
        f = f[f["domain"].isin(sel_domains) | f["domain"].isna()]
    if sel_types:
        f = f[f["job_type"].isin(sel_types) | f["job_type"].isna()]
    if sel_seniority:
        f = f[f["seniority"].isin(sel_seniority) | f["seniority"].isna()]
    if sel_modes:
        f = f[f["work_mode"].isin(sel_modes) | f["work_mode"].isna()]
    if sel_techs:
        matching = tech_df[tech_df["technology"].isin(sel_techs)]["post_id"].unique()
        f = f[f["post_id"].isin(matching)]
    if sel_subs:
        f = f[f["subreddit"].isin(sel_subs)]

    return f


# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
def render_kpis(filtered: pd.DataFrame, tech_df: pd.DataFrame) -> None:
    yesterday = pd.Timestamp.now(tz="UTC") - timedelta(days=1)
    new_24h = int((filtered["created_utc"] >= yesterday).sum()) if not filtered.empty else 0

    remote_pct = 0
    if not filtered.empty and "work_mode" in filtered.columns:
        remote_pct = int(100 * (filtered["work_mode"] == "Remote").sum() / max(len(filtered), 1))

    top_domain = "N/A"
    if not filtered.empty and "domain" in filtered.columns:
        vc = filtered["domain"].dropna().value_counts()
        if not vc.empty:
            top_domain = vc.index[0]

    tech_count = 0
    if not tech_df.empty and not filtered.empty:
        tech_count = tech_df[tech_df["post_id"].isin(filtered["post_id"])]["technology"].nunique()

    st.markdown(
        f"""
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-value">{len(filtered):,}</div>
                <div class="kpi-label">💼 Job Posts</div>
            </div>
            <div class="kpi-card green">
                <div class="kpi-value">{new_24h}</div>
                <div class="kpi-label">New Last 24h</div>
            </div>
            <div class="kpi-card orange">
                <div class="kpi-value">{remote_pct}%</div>
                <div class="kpi-label">Remote</div>
            </div>
            <div class="kpi-card pink">
                <div class="kpi-value">{top_domain}</div>
                <div class="kpi-label">Top Domain</div>
            </div>
            <div class="kpi-card teal">
                <div class="kpi-value">{tech_count}</div>
                <div class="kpi-label">Tech Skills</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tab 1 -- Browse Jobs
# ---------------------------------------------------------------------------
def render_browse(filtered: pd.DataFrame, tech_df: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No job posts match the current filters.")
        return

    sorted_df = filtered.sort_values("created_utc", ascending=False)
    PAGE_SIZE = 20
    total = len(sorted_df)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    col_info, col_page = st.columns([3, 1])
    with col_info:
        st.caption(f"{total:,} job posts found")
    with col_page:
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1,
                               step=1, label_visibility="collapsed")

    page_df = sorted_df.iloc[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    for _, row in page_df.iterrows():
        post_techs = tech_df[tech_df["post_id"] == row["post_id"]]["technology"].tolist() if not tech_df.empty else []

        badges = (
            (_badge(row["domain"], "b-domain") if pd.notna(row.get("domain")) else "")
            + _work_mode_badge(row.get("work_mode"))
            + _seniority_badge(row.get("seniority"))
            + _job_type_badge(row.get("job_type"))
        )

        tech_tags = "".join(f'<span class="tech-tag">{t}</span>' for t in post_techs[:10])

        excerpt = ""
        body = row.get("body") or ""
        if isinstance(body, str) and body.strip():
            excerpt = body.strip()[:220].replace("<", "&lt;").replace(">", "&gt;")
            if len(body) > 220:
                excerpt += "..."

        posted = _time_ago(row["created_utc"]) if pd.notna(row.get("created_utc")) else ""

        st.markdown(
            f"""
            <div class="job-card">
                <div class="job-card-title">
                    <a href="{row['post_url']}" target="_blank">&#8599; {row['title'][:120]}</a>
                </div>
                <div>{badges}</div>
                <div class="job-meta">
                    r/{row['subreddit']} &nbsp;·&nbsp;
                    {int(row.get('score', 0))} upvotes &nbsp;·&nbsp;
                    {int(row.get('num_comments', 0))} comments &nbsp;·&nbsp;
                    {posted}
                </div>
                {"<div class='job-excerpt'>" + excerpt + "</div>" if excerpt else ""}
                <div style="margin-top:0.4rem">{tech_tags}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(f"Page {page} of {total_pages}")


# ---------------------------------------------------------------------------
# Tab 2 -- Analytics
# ---------------------------------------------------------------------------
_LAYOUT = dict(height=320, margin=dict(l=0, r=0, t=20, b=0),
               plot_bgcolor="white", paper_bgcolor="white",
               font=dict(family="sans-serif", size=12))
_PRIMARY = "#6C63FF"
_PALETTE = px.colors.qualitative.Set2


def render_analytics(filtered: pd.DataFrame, tech_df: pd.DataFrame) -> None:
    if filtered.empty:
        st.info("No data available for the current filters.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">Job Volume Over Time</div>', unsafe_allow_html=True)
        if "date" in filtered.columns:
            vol = filtered.groupby("date").size().reset_index(name="count")
            fig = px.area(vol, x="date", y="count", color_discrete_sequence=[_PRIMARY])
            fig.update_layout(**_LAYOUT, xaxis_title="", yaxis_title="Posts")
            fig.update_traces(line_width=2, fillcolor="rgba(108,99,255,0.12)")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">Top Subreddits</div>', unsafe_allow_html=True)
        top_subs = filtered["subreddit"].value_counts().head(12).reset_index()
        top_subs.columns = ["Subreddit", "Posts"]
        fig = px.bar(top_subs, x="Posts", y="Subreddit", orientation="h",
                     color="Posts", color_continuous_scale="Purples")
        fig.update_layout(**_LAYOUT, yaxis=dict(autorange="reversed"),
                          showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="section-title">Jobs by Domain</div>', unsafe_allow_html=True)
        domain_vc = filtered["domain"].dropna().value_counts().reset_index()
        domain_vc.columns = ["Domain", "Count"]
        if not domain_vc.empty:
            fig = px.pie(domain_vc, values="Count", names="Domain",
                         hole=0.45, color_discrete_sequence=_PALETTE)
            fig.update_layout(**_LAYOUT)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        st.markdown('<div class="section-title">Work Mode Split</div>', unsafe_allow_html=True)
        mode_vc = filtered["work_mode"].dropna().value_counts().reset_index()
        mode_vc.columns = ["Mode", "Count"]
        if not mode_vc.empty:
            fig = px.pie(mode_vc, values="Count", names="Mode", hole=0.45,
                         color="Mode",
                         color_discrete_map={"Remote": "#10B981", "Hybrid": "#F59E0B", "On-site": "#EF4444"})
            fig.update_layout(**_LAYOUT)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    c5, c6 = st.columns(2)
    with c5:
        st.markdown('<div class="section-title">Seniority Distribution</div>', unsafe_allow_html=True)
        sen_order = ["Junior", "Mid", "Senior", "Lead/Principal"]
        sen_vc = filtered["seniority"].dropna().value_counts().reindex(sen_order).dropna().reset_index()
        sen_vc.columns = ["Level", "Count"]
        if not sen_vc.empty:
            fig = px.bar(sen_vc, x="Level", y="Count", color="Level",
                         color_discrete_sequence=["#10B981", "#2563EB", "#9333EA", "#92400E"])
            fig.update_layout(**_LAYOUT, showlegend=False, xaxis_title="", yaxis_title="Posts")
            st.plotly_chart(fig, use_container_width=True)

    with c6:
        st.markdown('<div class="section-title">Job Type Breakdown</div>', unsafe_allow_html=True)
        type_vc = filtered["job_type"].dropna().value_counts().reset_index()
        type_vc.columns = ["Type", "Count"]
        if not type_vc.empty:
            fig = px.bar(type_vc, x="Count", y="Type", orientation="h",
                         color="Count", color_continuous_scale="Blues")
            fig.update_layout(**_LAYOUT, yaxis=dict(autorange="reversed"),
                              showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Top 20 In-Demand Skills</div>', unsafe_allow_html=True)
    if not tech_df.empty:
        rel_tech = tech_df[tech_df["post_id"].isin(filtered["post_id"])]
        top_skills = rel_tech["technology"].value_counts().head(20).reset_index()
        top_skills.columns = ["Technology", "Count"]
        fig = px.bar(top_skills, x="Count", y="Technology", orientation="h",
                     color="Count", color_continuous_scale="Viridis")
        fig.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0),
                          plot_bgcolor="white", paper_bgcolor="white",
                          yaxis=dict(autorange="reversed"),
                          showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 3 -- Tech Trends
# ---------------------------------------------------------------------------
def render_tech_trends(filtered: pd.DataFrame, tech_df: pd.DataFrame) -> None:
    if filtered.empty or tech_df.empty:
        st.info("Not enough data to show tech trends.")
        return

    rel_tech = tech_df[tech_df["post_id"].isin(filtered["post_id"])]
    if rel_tech.empty:
        st.info("No tech stack data for the current filters.")
        return

    top8 = rel_tech["technology"].value_counts().head(8).index.tolist()
    merged = rel_tech.merge(filtered[["post_id", "week"]], on="post_id", how="left")
    merged = merged[merged["technology"].isin(top8)]
    weekly = merged.groupby(["week", "technology"]).size().reset_index(name="count")

    st.markdown('<div class="section-title">Weekly Tech Demand (Top 8)</div>', unsafe_allow_html=True)
    if not weekly.empty:
        fig = px.line(weekly, x="week", y="count", color="technology",
                      markers=True, color_discrete_sequence=px.colors.qualitative.Bold)
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                          plot_bgcolor="white", paper_bgcolor="white",
                          xaxis_title="Week", yaxis_title="Mentions", legend_title="Technology")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Tech Skills by Domain</div>', unsafe_allow_html=True)
    domain_tech = rel_tech.merge(filtered[["post_id", "domain"]], on="post_id", how="left").dropna(subset=["domain"])
    top20 = rel_tech["technology"].value_counts().head(20).index.tolist()
    domain_tech = domain_tech[domain_tech["technology"].isin(top20)]

    if not domain_tech.empty:
        pivot = (domain_tech.groupby(["domain", "technology"]).size()
                 .reset_index(name="count")
                 .pivot(index="domain", columns="technology", values="count")
                 .fillna(0))
        fig = px.imshow(pivot, color_continuous_scale="Purples", aspect="auto", text_auto=True)
        fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=0),
                          coloraxis_showscale=False, xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Common Tech Combinations</div>', unsafe_allow_html=True)
    post_techs = rel_tech.groupby("post_id")["technology"].apply(list)
    pairs: dict[tuple, int] = {}
    for techs in post_techs:
        techs_sorted = sorted(set(techs))
        for i in range(len(techs_sorted)):
            for j in range(i + 1, len(techs_sorted)):
                pair = (techs_sorted[i], techs_sorted[j])
                pairs[pair] = pairs.get(pair, 0) + 1

    if pairs:
        pair_df = (pd.DataFrame([{"Tech A": a, "Tech B": b, "Co-occurrences": c}
                                  for (a, b), c in pairs.items()])
                   .sort_values("Co-occurrences", ascending=False).head(15))
        st.dataframe(pair_df, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.markdown(
        """
        <h1 style="margin-bottom:0; color:#1E1B4B;">💼 Reddit Job Intelligence</h1>
        <p style="color:#9CA3AF; margin-top:0.2rem; font-size:0.88rem;">
            Daily job listings aggregated and classified from Reddit communities
        </p>
        """,
        unsafe_allow_html=True,
    )

    try:
        jobs_df, tech_df = load_data()
    except ConnectionError as exc:
        st.error(f"Database connection failed: {exc}")
        return

    if jobs_df.empty:
        st.info("No data yet. Run the pipeline first:\n\n```bash\npython -m src.pipeline.run\n```")
        return

    filtered = render_sidebar(jobs_df, tech_df)
    render_kpis(filtered, tech_df)

    tab1, tab2, tab3 = st.tabs(["📋  Browse Jobs", "📊  Analytics", "⚙️  Tech Trends"])
    with tab1:
        render_browse(filtered, tech_df)
    with tab2:
        render_analytics(filtered, tech_df)
    with tab3:
        render_tech_trends(filtered, tech_df)

    st.markdown(
        """
        <div style="text-align:center; color:#D1D5DB; font-size:0.75rem; margin-top:2rem;
                    padding-top:1rem; border-top:1px solid #E5E7EB;">
            Reddit Job Intelligence · Data from public Reddit posts · Built with Streamlit and Plotly
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
