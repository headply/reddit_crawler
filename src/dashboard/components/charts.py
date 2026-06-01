"""Plotly chart helpers with shared styling."""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PALETTE = [
    "#0F766E",
    "#2563EB",
    "#F59E0B",
    "#EF4444",
    "#10B981",
    "#0EA5E9",
    "#14B8A6",
    "#8B5CF6",
]

FONT = dict(family="'Space Grotesk', sans-serif", size=12, color="#0F172A")
MARGIN = dict(l=8, r=8, t=40, b=8)


def _base_layout(**kwargs: Any) -> dict[str, Any]:
    axes = dict(showgrid=True, gridcolor="#E2E8F0", linecolor="#E2E8F0")
    layout = {
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "font": FONT,
        "margin": MARGIN,
        "xaxis": {**axes, **kwargs.pop("xaxis", {})},
        "yaxis": {**axes, **kwargs.pop("yaxis", {})},
    }
    layout.update(kwargs)
    return layout


def render_chart(fig: go.Figure, height: int | None = None) -> None:
    """Render a Plotly chart with standard config."""
    if height is not None:
        fig.update_layout(height=height)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_empty_state(message: str = "Not enough data yet") -> None:
    """Render a clean empty-state placeholder."""
    st.markdown(f"<div class='empty-state'>{message}</div>", unsafe_allow_html=True)


def build_line_chart(
    df,
    x: str,
    y: str,
    color: str | None = None,
    title: str | None = None,
) -> go.Figure:
    """Build a line chart with shared defaults."""
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        markers=True,
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(**_base_layout(title=title or ""))
    return fig


def build_bar_chart(
    df,
    x: str,
    y: str,
    orientation: str = "v",
    title: str | None = None,
    color: str | None = None,
) -> go.Figure:
    """Build a bar chart with shared defaults."""
    fig = px.bar(
        df,
        x=x,
        y=y,
        orientation=orientation,
        color=color,
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(**_base_layout(title=title or ""))
    if orientation == "h":
        fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig


def build_donut(
    df,
    values: str,
    names: str,
    title: str | None = None,
    color: str | None = None,
) -> go.Figure:
    """Build a donut chart with shared defaults."""
    fig = px.pie(
        df,
        values=values,
        names=names,
        hole=0.55,
        color=color,
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(textposition="none")
    fig.update_layout(
        **_base_layout(
            title=title or "",
            showlegend=True,
            margin=dict(l=8, r=8, t=8, b=8),
        )
    )
    return fig


def build_heatmap(df, title: str | None = None) -> go.Figure:
    """Build a heatmap from a pivoted dataframe."""
    fig = px.imshow(
        df,
        color_continuous_scale=["#F8FAFC", "#0F766E"],
        aspect="auto",
        text_auto=True,
    )
    fig.update_layout(
        **_base_layout(
            title=title or "",
            coloraxis_showscale=False,
            margin=dict(l=8, r=8, t=32, b=8),
        )
    )
    fig.update_traces(textfont_size=10)
    return fig


def build_box_plot(df, x: str, y: str, color: str | None = None) -> go.Figure:
    """Build a box plot using raw samples."""
    fig = px.box(
        df,
        x=x,
        y=y,
        color=color,
        points="outliers",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(**_base_layout())
    return fig
