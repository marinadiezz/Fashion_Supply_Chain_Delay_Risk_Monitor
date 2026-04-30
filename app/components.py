from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PALETTE = ["#2f6f73", "#466a8f", "#6a7d4f", "#b7791f", "#c5534f", "#68717a", "#8b6f47"]
BAND_COLORS = {"Ready": "#3d7a57", "Watch": "#b7791f", "At Risk": "#c5534f", "Critical": "#9f2d3a"}
SEVERITY_COLORS = {"Low": "#3d7a57", "Medium": "#b7791f", "High": "#c5534f", "Critical": "#9f2d3a"}
SUPPLIER_BAND_COLORS = {
    "Low Risk": "#3d7a57",
    "Monitor": "#b7791f",
    "High Variance": "#c5534f",
    "Critical Watchlist": "#9f2d3a",
}
STATUS_COLORS = {
    "Completed": "#3d7a57",
    "Closed": "#3d7a57",
    "Resolved": "#3d7a57",
    "Received": "#3d7a57",
    "Ready": "#3d7a57",
    "Watch": "#b7791f",
    "In Progress": "#466a8f",
    "Monitoring": "#466a8f",
    "Confirmed": "#466a8f",
    "In Transit": "#466a8f",
    "Not Started": "#68717a",
    "In Review": "#b7791f",
    "At Risk": "#c5534f",
    "Delayed": "#c5534f",
    "Partial": "#c5534f",
    "Overdue": "#c5534f",
    "Blocked": "#9f2d3a",
    "Critical": "#9f2d3a",
    "Open": "#c5534f",
    "Escalated": "#9f2d3a",
    "Mitigating": "#466a8f",
}
PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]


def pretty_label(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace("_", " ").strip()
    return re.sub(r"\s+", " ", text).title()


def fmt_date(value: object) -> str:
    if pd.isna(value) or value == "":
        return ""
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def fmt_days(value: object) -> str:
    if pd.isna(value):
        return "0.0 days"
    return f"{float(value):.1f} days"


def fmt_score(value: object) -> str:
    if pd.isna(value):
        return "0.0"
    return f"{float(value):.1f}"


def signed_days(value: object) -> str:
    if pd.isna(value):
        return "+0.0 days"
    return f"{float(value):+.1f} days"


def metric_card(label: str, value: str, caption: str = "") -> None:
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-caption'>{caption}</div></div>",
        unsafe_allow_html=True,
    )


def insight_card(title: str, body: str) -> None:
    st.markdown(f"<div class='insight'><b>{title}</b> {body}</div>", unsafe_allow_html=True)


def filter_chips(filters: dict[str, Iterable[str]]) -> None:
    chips = []
    for label, values in filters.items():
        if isinstance(values, tuple):
            display = f"{values[0]} to {values[1]}"
        else:
            values = list(values or [])
            display = ", ".join(map(str, values[:3]))
            if len(values) > 3:
                display += f" +{len(values) - 3}"
        if display:
            chips.append(f"<span class='filter-chip'><b>{label}:</b> {display}</span>")
    if chips:
        st.markdown("<div class='chip-row'>" + "".join(chips) + "</div>", unsafe_allow_html=True)


def apply_chart_theme(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        colorway=PALETTE,
        margin=dict(l=36, r=28, t=82, b=72),
        font=dict(family="Inter, Arial, sans-serif", color="#17202a", size=13),
        title=dict(x=0, xanchor="left", y=0.98, yanchor="top", pad=dict(t=8, b=18)),
        title_font=dict(size=17, family="Inter, Arial, sans-serif", color="#17202a"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color="#39424c", size=11),
            title_font=dict(color="#39424c", size=11),
            bgcolor="rgba(255,255,255,.82)",
            bordercolor="rgba(214,219,224,.8)",
            borderwidth=1,
            itemwidth=30,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        hovermode="closest",
        hoverdistance=18,
        separators=",.",
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#c8d1d8",
            align="left",
            font=dict(color="#17202a", family="Inter, Arial, sans-serif", size=12),
        ),
    )
    fig.update_traces(marker_line_width=0.5, marker_line_color="rgba(23,32,42,.18)", selector=dict(type="bar"))
    fig.update_traces(marker_line_width=0.7, marker_line_color="rgba(23,32,42,.24)", selector=dict(type="scatter"))
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(
        title_font=dict(color="#39424c", size=12),
        tickfont=dict(color="#39424c", size=11),
        gridcolor="#e9edf1",
        linecolor="#ccd4dc",
        zerolinecolor="#ccd4dc",
        automargin=True,
        ticks="outside",
        ticklen=4,
        separatethousands=True,
    )
    fig.update_yaxes(
        title_font=dict(color="#39424c", size=12),
        tickfont=dict(color="#39424c", size=11),
        gridcolor="#f1f4f6",
        linecolor="#ccd4dc",
        zerolinecolor="#ccd4dc",
        automargin=True,
        ticks="outside",
        ticklen=4,
    )
    return fig


def clean_table(
    df: pd.DataFrame,
    columns: list[str],
    rename: dict[str, str],
    date_cols: list[str] | None = None,
    day_cols: list[str] | None = None,
    score_cols: list[str] | None = None,
    bool_cols: dict[str, tuple[str, str]] | None = None,
) -> pd.DataFrame:
    out = df[[c for c in columns if c in df.columns]].copy()
    for col in date_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(fmt_date)
    for col in day_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(fmt_days)
    for col in score_cols or []:
        if col in out.columns:
            out[col] = out[col].apply(fmt_score)
    for col, labels in (bool_cols or {}).items():
        if col in out.columns:
            yes, no = labels
            out[col] = out[col].map(lambda v: yes if bool(v) else no)
    for col in out.select_dtypes(include=["object"]).columns:
        if col.endswith("workstream") or col in {"workstream", "sku_family", "risk_type", "transport_mode"}:
            out[col] = out[col].map(pretty_label)
    return out.rename(columns=rename)


def render_business_table(df: pd.DataFrame, height: int = 360) -> None:
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        height=height,
    )


def supplier_detail_panel(supplier: pd.Series, risks: pd.DataFrame, actions: pd.DataFrame, incidents: pd.DataFrame) -> None:
    supplier_id = supplier.get("supplier_id")
    related_incidents = incidents[incidents["supplier_id"] == supplier_id] if "supplier_id" in incidents.columns else incidents.iloc[0:0]
    linked_collections = str(supplier.get("linked_collections", "")).split(", ")
    related_risks = risks[risks["collection_name"].isin(linked_collections)] if "collection_name" in risks.columns else risks.iloc[0:0]
    related_actions = actions[actions["collection_name"].isin(linked_collections)] if "collection_name" in actions.columns else actions.iloc[0:0]
    st.markdown(
        f"""
        <div class="detail-panel">
        <div class="eyebrow dark">Supplier detail</div>
        <h3>{supplier.get('supplier_name', 'Selected supplier')}</h3>
        <p><b>Location:</b> {supplier.get('supplier_city', '')}, {supplier.get('country', '')} | <b>Risk band:</b> {supplier.get('supplier_risk_band', '')}</p>
        <p><b>Average delay:</b> {fmt_days(supplier.get('avg_delay', 0))} | <b>Lead-time variance:</b> {signed_days(supplier.get('lead_time_variance', 0))} | <b>Incidents:</b> {int(supplier.get('incidents', 0))} | <b>Reliability:</b> {fmt_score(supplier.get('reliability_score_base', 0))}/100</p>
        <p><b>PM action:</b> {supplier.get('suggested_pm_action', 'Review supplier status')}</p>
        <p><b>Related pressure:</b> {len(related_risks[related_risks.get('is_open', False)]) if not related_risks.empty else 0} open linked risks, {len(related_actions[related_actions.get('is_overdue', False)]) if not related_actions.empty else 0} overdue actions, {len(related_incidents[related_incidents.get('status', '').isin(['Open', 'In Review'])]) if not related_incidents.empty else 0} open incidents.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def collection_detail_panel(collection: pd.Series, milestones: pd.DataFrame, risks: pd.DataFrame, actions: pd.DataFrame, pos: pd.DataFrame) -> None:
    collection_id = collection.get("collection_id")
    m = milestones[milestones["collection_id"] == collection_id]
    r = risks[risks["collection_id"] == collection_id]
    a = actions[actions["collection_id"] == collection_id]
    p = pos[pos["collection_id"] == collection_id]
    blocked = int(m["status"].eq("Blocked").sum()) if not m.empty else 0
    critical = int(((r["severity"] == "Critical") & r["is_open"]).sum()) if not r.empty else 0
    overdue = int(a["is_overdue"].sum()) if not a.empty else 0
    delay = float(pd.concat([m["delay_days"], p["delay_days"]], ignore_index=True).fillna(0).mean()) if not m.empty or not p.empty else 0
    action = "Escalate launch governance" if critical or blocked else "Maintain weekly PMO cadence"
    st.markdown(
        f"""
        <div class="detail-panel">
        <div class="eyebrow dark">Collection detail</div>
        <h3>{collection.get('collection_name', 'Selected collection')}</h3>
        <p><b>Brand:</b> {collection.get('brand_name', '')} | <b>Market:</b> {collection.get('market', '')} | <b>Launch:</b> {fmt_date(collection.get('launch_date', ''))}</p>
        <p><b>Readiness:</b> {fmt_score(collection.get('readiness_score', 0))}/100 ({collection.get('readiness_band', '')}) | <b>Average delay:</b> {fmt_days(delay)} | <b>Blocked milestones:</b> {blocked}</p>
        <p><b>Open critical risks:</b> {critical} | <b>Overdue actions:</b> {overdue} | <b>Recommended PM action:</b> {action}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
