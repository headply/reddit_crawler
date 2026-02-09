"""Streamlit dashboard for the Reddit Job Intelligence Platform.

Interactive dashboard with filters, charts, and a hot jobs section.
Uses Material Design icons instead of emojis for a professional look.
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
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Reddit Job Intelligence",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='%234A90D9' d='M20 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v11c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zM10 4h4v2h-4V4z'/></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for polish
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Import Material Icons */
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
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
    .icon-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .icon-header .material-icons {
        font-size: 1.5rem;
        color: #667eea;
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
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }
    div[data-testid="stSidebar"] {
        background: #f8f9fa;
    }
</style>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
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
# Helper to render Material icons
# ---------------------------------------------------------------------------
def icon(name: str) -> str:
    """Return an inline Material Icon span."""
    return f'<span class="material-icons" style="vertical-align: middle;">{name}</span>'


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------
def main() -> None:
    """Render the full dashboard."""
    # Header
    st.markdown(
        f"""<h1 style="margin-bottom:0;">{icon("work")} Reddit Job Intelligence</h1>
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
        st.markdown(f'### {icon("filter_list")} Filters', unsafe_allow_html=True)

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
            f'<small>{icon("schedule")} Data refreshes daily</small>',
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
                <p>{icon("work")} Job Posts</p>
            </div>""",
            unsafe_allow_html=True,
        )
    with col2:
        avg_sentiment = filtered["sentiment_score"].mean() if not filtered.empty else 0
        st.markdown(
            f"""<div class="metric-card">
                <h3>{avg_sentiment:.2f}</h3>
                <p>{icon("sentiment_satisfied")} Avg Sentiment</p>
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
            f'#### {icon("mood")} Sentiment Distribution',
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
        f'### {icon("local_fire_department")} Hot Jobs Today',
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
                        {icon("open_in_new")} {row['title'][:100]}
                    </a></h4>
                    <small style="color: #888;">
                        r/{row['subreddit']} &middot;
                        {icon("thumb_up")} {row.get('score', 0)} &middot;
                        {icon("comment")} {row.get('num_comments', 0)}
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
        f'### {icon("table_chart")} All Job Listings',
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
