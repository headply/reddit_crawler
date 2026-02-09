"""Streamlit dashboard for the Reddit Job Intelligence Platform.

Interactive dashboard with filters, charts, and a hot jobs section.
Uses inline SVG icons for a professional look without external dependencies.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.db import get_connection, init_db

# ---------------------------------------------------------------------------
# Inline SVG icons (no external font dependency)
# ---------------------------------------------------------------------------
_ICONS: dict[str, str] = {
    "briefcase": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 3h-8a2 2 0 0 0-2 2v2h12V5a2 2 0 0 0-2-2z"/></svg>',
    "filter": '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
    "trending_up": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "bar_chart": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "smile": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>',
    "pie_chart": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg>',
    "flame": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#e65100" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M12 22c-4.97 0-9-2.69-9-6 0-4 5-11 9-14 4 3 9 10 9 14 0 3.31-4.03 6-9 6z"/></svg>',
    "table": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/></svg>',
    "external_link": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
    "thumb_up": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M14 9V5a3 3 0 0 0-6 0v4"/><path d="M2 11h3v10H2z"/><path d="M5 21h9.5a2.5 2.5 0 0 0 2.45-2l1.55-7.8A2 2 0 0 0 16.56 9H10V5a1 1 0 0 0-1-1l-4 7v10"/></svg>',
    "message": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "forum": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "code": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    "clock": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "info": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
}


def icon(name: str) -> str:
    """Return an inline SVG icon by name.

    Args:
        name: Icon identifier key from _ICONS.

    Returns:
        HTML string with the inline SVG, or empty string if not found.
    """
    return _ICONS.get(name, "")


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Reddit Job Intelligence",
    page_icon="briefcase",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for polish
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .metric-card h3 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-card p {
        margin: 0.3rem 0 0;
        font-size: 0.85rem;
        opacity: 0.9;
    }
    .metric-card svg {
        stroke: white;
    }
    .hot-job-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        background: #fafafa;
        transition: box-shadow 0.2s;
    }
    .hot-job-card:hover {
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    .hot-job-card h4 {
        margin: 0 0 0.4rem;
        font-size: 1rem;
    }
    .hot-job-card a {
        color: #667eea;
        text-decoration: none;
        font-weight: 500;
    }
    .tag {
        display: inline-block;
        background: #e8eaf6;
        color: #3949ab;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        margin: 2px;
    }
    div[data-testid="stSidebar"] {
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load posts and classifications from the database.

    Returns:
        Tuple of (jobs DataFrame, tech stack DataFrame).
    """
    init_db()
    conn = get_connection()
    try:
        jobs_df = pd.read_sql_query(
            """SELECT p.post_id, p.title, p.body, p.author, p.subreddit,
                      p.score, p.num_comments, p.created_utc, p.post_url,
                      jc.is_job, jc.job_type, jc.seniority, jc.domain,
                      jc.work_mode, jc.sentiment_score, jc.urgency_score
               FROM posts p
               LEFT JOIN job_classifications jc ON p.post_id = jc.post_id""",
            conn,
        )
        tech_df = pd.read_sql_query(
            "SELECT post_id, technology FROM tech_stack",
            conn,
        )
    finally:
        conn.close()

    if not jobs_df.empty and "created_utc" in jobs_df.columns:
        jobs_df["created_utc"] = pd.to_datetime(jobs_df["created_utc"])
        jobs_df["date"] = jobs_df["created_utc"].dt.date

    return jobs_df, tech_df


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the full dashboard."""
    # Header
    st.markdown(
        f"""<h1 style="margin-bottom:0;">{icon("briefcase")} Reddit Job Intelligence</h1>
        <p style="color: #888; margin-top: 0.2rem;">
            Automated daily insights from Reddit job communities
        </p>""",
        unsafe_allow_html=True,
    )

    jobs_df, tech_df = load_data()

    if jobs_df.empty:
        st.info("No data available yet. Run the pipeline first to populate the database.")
        st.markdown(
            """
            **Quick start:**
            ```bash
            # Set up your .env file with Reddit API credentials
            cp .env.example .env
            # Edit .env with your credentials

            # Run the pipeline
            python -m src.pipeline.run
            ```
            """
        )
        return

    # Filter to job posts only
    job_posts = jobs_df[jobs_df["is_job"] == 1].copy() if "is_job" in jobs_df.columns else jobs_df.copy()

    # ----- Sidebar filters -----
    with st.sidebar:
        st.markdown(f'### {icon("filter")} Filters', unsafe_allow_html=True)

        # Job type filter
        job_types = sorted(job_posts["job_type"].dropna().unique()) if "job_type" in job_posts.columns else []
        selected_types = st.multiselect("Job Type", job_types, default=job_types)

        # Domain filter
        domains = sorted(job_posts["domain"].dropna().unique()) if "domain" in job_posts.columns else []
        selected_domains = st.multiselect("Domain", domains, default=domains)

        # Work mode filter
        work_modes = sorted(job_posts["work_mode"].dropna().unique()) if "work_mode" in job_posts.columns else []
        selected_modes = st.multiselect("Work Mode", work_modes, default=work_modes)

        # Tech stack filter
        all_techs = sorted(tech_df["technology"].unique()) if not tech_df.empty else []
        selected_techs = st.multiselect("Tech Stack", all_techs)

        st.markdown("---")
        st.markdown(
            f'<small>{icon("clock")} Data refreshes daily</small>',
            unsafe_allow_html=True,
        )

    # ----- Apply filters -----
    filtered = job_posts.copy()
    if selected_types:
        filtered = filtered[filtered["job_type"].isin(selected_types) | filtered["job_type"].isna()]
    if selected_domains:
        filtered = filtered[filtered["domain"].isin(selected_domains) | filtered["domain"].isna()]
    if selected_modes:
        filtered = filtered[filtered["work_mode"].isin(selected_modes) | filtered["work_mode"].isna()]
    if selected_techs:
        matching_ids = tech_df[tech_df["technology"].isin(selected_techs)]["post_id"].unique()
        filtered = filtered[filtered["post_id"].isin(matching_ids)]

    # ----- Metric cards -----
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""<div class="metric-card">
                <h3>{len(filtered)}</h3>
                <p>{icon("briefcase")} Job Posts</p>
            </div>""",
            unsafe_allow_html=True,
        )
    with col2:
        avg_sentiment = filtered["sentiment_score"].mean() if not filtered.empty else 0
        st.markdown(
            f"""<div class="metric-card">
                <h3>{avg_sentiment:.2f}</h3>
                <p>{icon("smile")} Avg Sentiment</p>
            </div>""",
            unsafe_allow_html=True,
        )
    with col3:
        total_subs = filtered["subreddit"].nunique() if not filtered.empty else 0
        st.markdown(
            f"""<div class="metric-card">
                <h3>{total_subs}</h3>
                <p>{icon("forum")} Subreddits</p>
            </div>""",
            unsafe_allow_html=True,
        )
    with col4:
        tech_count = tech_df[tech_df["post_id"].isin(filtered["post_id"])]["technology"].nunique() if not filtered.empty else 0
        st.markdown(
            f"""<div class="metric-card">
                <h3>{tech_count}</h3>
                <p>{icon("code")} Technologies</p>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ----- Charts -----
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown(
            f'#### {icon("trending_up")} Job Volume Over Time',
            unsafe_allow_html=True,
        )
        if not filtered.empty and "date" in filtered.columns:
            volume = filtered.groupby("date").size().reset_index(name="count")
            fig = px.area(
                volume,
                x="date",
                y="count",
                color_discrete_sequence=["#667eea"],
            )
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Posts",
                height=320,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No data for this period.")

    with chart_col2:
        st.markdown(
            f'#### {icon("bar_chart")} Top Skills in Demand',
            unsafe_allow_html=True,
        )
        if not tech_df.empty and not filtered.empty:
            relevant_tech = tech_df[tech_df["post_id"].isin(filtered["post_id"])]
            top_skills = relevant_tech["technology"].value_counts().head(15).reset_index()
            top_skills.columns = ["Technology", "Count"]
            fig = px.bar(
                top_skills,
                x="Count",
                y="Technology",
                orientation="h",
                color="Count",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                height=320,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=False,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No tech stack data available.")

    # Second row of charts
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.markdown(
            f'#### {icon("smile")} Sentiment Distribution',
            unsafe_allow_html=True,
        )
        if not filtered.empty and "sentiment_score" in filtered.columns:
            fig = px.histogram(
                filtered,
                x="sentiment_score",
                nbins=30,
                color_discrete_sequence=["#764ba2"],
            )
            fig.update_layout(
                xaxis_title="Sentiment Score",
                yaxis_title="Count",
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No sentiment data available.")

    with chart_col4:
        st.markdown(
            f'#### {icon("pie_chart")} Jobs by Domain',
            unsafe_allow_html=True,
        )
        if not filtered.empty and "domain" in filtered.columns:
            domain_counts = filtered["domain"].dropna().value_counts().reset_index()
            domain_counts.columns = ["Domain", "Count"]
            if not domain_counts.empty:
                fig = px.pie(
                    domain_counts,
                    values="Count",
                    names="Domain",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(
                    height=300,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("No domain data available.")
        else:
            st.caption("No domain data available.")

    # ----- Hot Jobs Today -----
    st.markdown("---")
    st.markdown(
        f'### {icon("flame")} Hot Jobs Today',
        unsafe_allow_html=True,
    )
    st.caption("High urgency + positive sentiment posts")

    if not filtered.empty:
        hot_jobs = filtered[
            (filtered["urgency_score"] > 0.2) & (filtered["sentiment_score"] > 0)
        ].sort_values(
            ["urgency_score", "sentiment_score"], ascending=False
        ).head(10)

        if hot_jobs.empty:
            hot_jobs = filtered.sort_values("score", ascending=False).head(5)
            st.caption("(Showing top posts by score)")

        for _, row in hot_jobs.iterrows():
            post_techs = tech_df[tech_df["post_id"] == row["post_id"]]["technology"].tolist()
            tech_tags = " ".join(f'<span class="tag">{t}</span>' for t in post_techs)
            meta_parts = []
            if pd.notna(row.get("job_type")):
                meta_parts.append(row["job_type"])
            if pd.notna(row.get("work_mode")):
                meta_parts.append(row["work_mode"])
            if pd.notna(row.get("seniority")):
                meta_parts.append(row["seniority"])
            meta_line = " &middot; ".join(meta_parts) if meta_parts else ""

            st.markdown(
                f"""<div class="hot-job-card">
                    <h4><a href="{row['post_url']}" target="_blank">
                        {icon("external_link")} {row['title'][:100]}
                    </a></h4>
                    <small style="color: #888;">
                        r/{row['subreddit']} &middot;
                        {icon("thumb_up")} {row.get('score', 0)} &middot;
                        {icon("message")} {row.get('num_comments', 0)}
                        {(' &middot; ' + meta_line) if meta_line else ''}
                    </small><br>
                    {tech_tags}
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No hot jobs to display.")

    # ----- All Jobs Table -----
    st.markdown("---")
    st.markdown(
        f'### {icon("table")} All Job Listings',
        unsafe_allow_html=True,
    )

    if not filtered.empty:
        display_cols = ["title", "subreddit", "job_type", "domain", "work_mode",
                        "seniority", "sentiment_score", "urgency_score", "score", "post_url"]
        available_cols = [c for c in display_cols if c in filtered.columns]
        display_df = filtered[available_cols].copy()
        display_df = display_df.rename(columns={
            "title": "Title",
            "subreddit": "Subreddit",
            "job_type": "Type",
            "domain": "Domain",
            "work_mode": "Work Mode",
            "seniority": "Seniority",
            "sentiment_score": "Sentiment",
            "urgency_score": "Urgency",
            "score": "Score",
            "post_url": "Link",
        })
        st.dataframe(
            display_df,
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="View"),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("No listings match the current filters.")

    # Footer
    st.markdown("---")
    st.markdown(
        f"""<div style="text-align: center; color: #aaa; font-size: 0.8rem;">
            {icon("info")} Reddit Job Intelligence Platform &middot;
            Data sourced from public Reddit posts &middot;
            Built with Streamlit & Plotly
        </div>""",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
