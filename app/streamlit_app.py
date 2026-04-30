from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
APP_DIR = ROOT / "app"
for path in (SRC, APP_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from calculate_kpis import REFERENCE_DATE, portfolio_kpis, supplier_scorecard
from risk_scoring import calculate_readiness_scores, risk_exposure_by_workstream
from utils import load_all, pct
from components import (
    BAND_COLORS,
    PRIORITY_ORDER,
    SEVERITY_COLORS,
    SEVERITY_ORDER,
    STATUS_COLORS,
    SUPPLIER_BAND_COLORS,
    apply_chart_theme,
    clean_table,
    collection_detail_panel,
    filter_chips,
    fmt_date,
    insight_card,
    metric_card,
    pretty_label,
    render_business_table,
    supplier_detail_panel,
)


st.set_page_config(page_title="Fashion Supply Chain Delay & Risk Monitor", page_icon="F", layout="wide")


@st.cache_data
def get_data() -> dict[str, pd.DataFrame]:
    return load_all(processed=True)


def load_css() -> None:
    css_path = Path(__file__).with_name("style.css")
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def reset_filters() -> None:
    for key in list(st.session_state):
        if key.startswith("flt_"):
            del st.session_state[key]


def multiselect_filter(label: str, values: pd.Series, key: str, formatter=None) -> list:
    options = sorted([v for v in values.dropna().unique()])
    return st.multiselect(label, options=options, key=key, format_func=formatter or (lambda x: x))


def sidebar_filters(data: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    st.sidebar.markdown("### Launch Control Filters")
    st.sidebar.button("Reset filters", on_click=reset_filters, width="stretch")

    collections = data["collections"].copy()
    date_min = pd.to_datetime(collections["launch_date"]).min().date()
    date_max = pd.to_datetime(collections["launch_date"]).max().date()

    with st.sidebar.expander("Portfolio", expanded=True):
        brands = multiselect_filter("Brand", collections["brand_name"], "flt_brand")
        selected_collections = multiselect_filter("Collection", collections["collection_name"], "flt_collection")
        markets = multiselect_filter("Market", collections["market"], "flt_market")
        seasons = multiselect_filter("Season", collections["season"], "flt_season")
        channels = multiselect_filter("Launch channel", collections["launch_channel"], "flt_channel")
        date_range = st.date_input("Launch date range", value=(date_min, date_max), min_value=date_min, max_value=date_max, key="flt_date_range")

    mask = pd.Series(True, index=collections.index)
    if brands:
        mask &= collections["brand_name"].isin(brands)
    if selected_collections:
        mask &= collections["collection_name"].isin(selected_collections)
    if markets:
        mask &= collections["market"].isin(markets)
    if seasons:
        mask &= collections["season"].isin(seasons)
    if channels:
        mask &= collections["launch_channel"].isin(channels)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        mask &= pd.to_datetime(collections["launch_date"]).dt.date.between(date_range[0], date_range[1])

    collections = collections[mask]
    collection_ids = set(collections["collection_id"])
    filtered = {k: v.copy() for k, v in data.items()}
    filtered["collections"] = collections
    for name in ["purchase_orders", "milestones", "risks", "incidents", "actions"]:
        filtered[name] = filtered[name][filtered[name]["collection_id"].isin(collection_ids)]

    with st.sidebar.expander("Operations", expanded=False):
        workstreams = multiselect_filter("Workstream", filtered["milestones"]["workstream"] if not filtered["milestones"].empty else pd.Series(dtype=str), "flt_workstream", pretty_label)
        milestone_status = multiselect_filter("Milestone status", filtered["milestones"]["status"] if not filtered["milestones"].empty else pd.Series(dtype=str), "flt_milestone_status")

    with st.sidebar.expander("Risk", expanded=False):
        severities = multiselect_filter("Risk severity", filtered["risks"]["severity"] if not filtered["risks"].empty else pd.Series(dtype=str), "flt_severity")
        risk_status = multiselect_filter("Risk status", filtered["risks"]["status"] if not filtered["risks"].empty else pd.Series(dtype=str), "flt_risk_status")

    with st.sidebar.expander("Supplier", expanded=False):
        suppliers = multiselect_filter("Supplier", filtered["purchase_orders"]["supplier_name"] if not filtered["purchase_orders"].empty else pd.Series(dtype=str), "flt_supplier")
        transport_modes = multiselect_filter("Transport mode", filtered["purchase_orders"]["transport_mode"] if "transport_mode" in filtered["purchase_orders"].columns else pd.Series(dtype=str), "flt_transport")

    if workstreams:
        filtered["milestones"] = filtered["milestones"][filtered["milestones"]["workstream"].isin(workstreams)]
        filtered["risks"] = filtered["risks"][filtered["risks"]["workstream"].isin(workstreams)]
        filtered["actions"] = filtered["actions"][filtered["actions"]["workstream"].isin(workstreams)]
    if milestone_status:
        filtered["milestones"] = filtered["milestones"][filtered["milestones"]["status"].isin(milestone_status)]
    if severities:
        filtered["risks"] = filtered["risks"][filtered["risks"]["severity"].isin(severities)]
        filtered["actions"] = filtered["actions"][filtered["actions"]["severity"].isin(severities)]
    if risk_status:
        filtered["risks"] = filtered["risks"][filtered["risks"]["status"].isin(risk_status)]
    if suppliers:
        supplier_ids = set(filtered["purchase_orders"].loc[filtered["purchase_orders"]["supplier_name"].isin(suppliers), "supplier_id"])
        filtered["purchase_orders"] = filtered["purchase_orders"][filtered["purchase_orders"]["supplier_id"].isin(supplier_ids)]
        filtered["incidents"] = filtered["incidents"][filtered["incidents"]["supplier_id"].isin(supplier_ids)]
    if transport_modes and "transport_mode" in filtered["purchase_orders"].columns:
        filtered["purchase_orders"] = filtered["purchase_orders"][filtered["purchase_orders"]["transport_mode"].isin(transport_modes)]

    supplier_ids = set(filtered["purchase_orders"]["supplier_id"]).union(set(filtered["incidents"]["supplier_id"]))
    filtered["suppliers"] = filtered["suppliers"][filtered["suppliers"]["supplier_id"].isin(supplier_ids)] if supplier_ids else filtered["suppliers"].iloc[0:0]

    active_filters = {
        "Brand": brands,
        "Market": markets,
        "Season": seasons,
        "Channel": channels,
        "Launch window": date_range if isinstance(date_range, tuple) and len(date_range) == 2 else (),
        "Workstream": [pretty_label(v) for v in workstreams],
        "Supplier": suppliers,
        "Severity": severities,
    }
    return filtered, active_filters


def executive_text(data: dict[str, pd.DataFrame], readiness: pd.DataFrame) -> str:
    if data["milestones"].empty:
        return "No milestones match the current filters, so launch health cannot be interpreted from this selection."
    pressure = data["milestones"].groupby("workstream")["delay_days"].sum().sort_values(ascending=False).index[0]
    blocked = int(data["milestones"]["status"].eq("Blocked").sum())
    critical = int(((data["risks"]["severity"] == "Critical") & data["risks"]["is_open"]).sum()) if not data["risks"].empty else 0
    body = (
        f"Current launch health is stable but not clean. Risk is concentrated in {pretty_label(pressure)}, "
        f"where blocked milestones and unresolved risks are increasing launch governance pressure. "
        f"The filtered view contains {blocked} blocked milestones and {critical} open critical risks."
    )
    return body


def delay_text(data: dict[str, pd.DataFrame]) -> str:
    if data["milestones"].empty:
        return "No delay records match the active filters."
    worst = data["milestones"].groupby("collection_name")["delay_days"].sum().sort_values(ascending=False)
    collection = worst.index[0] if not worst.empty else "the filtered portfolio"
    return (
        f"Most delay pressure is not coming from average delay alone, but from repeated slippage in {collection}. "
        "This is the kind of pattern that can quietly move from production into logistics, content readiness and final launch approval."
    )


def risk_text(data: dict[str, pd.DataFrame]) -> str:
    if data["risks"].empty:
        return "No risks match the active filters."
    risk_type = data["risks"][data["risks"]["is_open"]].groupby("risk_type")["risk_score"].sum().sort_values(ascending=False)
    top = pretty_label(risk_type.index[0]) if not risk_type.empty else "open operational risk"
    return (
        f"Critical risk exposure is led by {top}. These risks are not isolated because they can affect downstream "
        "warehouse allocation, e-commerce readiness and the final go-live decision."
    )


def supplier_text(scorecard: pd.DataFrame) -> str:
    if scorecard.empty:
        return "No suppliers match the active filters."
    supplier = scorecard.iloc[0]
    return (
        f"The supplier watchlist should be treated as a sourcing review input, not just a delay ranking. "
        f"{supplier['supplier_name']} currently carries the highest operational exposure and needs: {supplier['suggested_pm_action']}."
    )


def dependency_text(data: dict[str, pd.DataFrame]) -> str:
    blocked = int(data["milestones"]["status"].eq("Blocked").sum()) if not data["milestones"].empty else 0
    return (
        f"Blocked dependencies are the strongest PMO signal in this dashboard. There are {blocked} blocked milestones in the current view; "
        "a delayed upstream approval can create artificial readiness confidence if only final milestones are monitored."
    )


def update_hover(fig, template: str):
    fig.update_traces(hovertemplate=template)
    return fig


def build_scorecard(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return supplier_scorecard(data["purchase_orders"], data["suppliers"], data["incidents"], data["risks"])


def hero(data: dict[str, pd.DataFrame]) -> None:
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">Executive launch control tower</div>
          <h1>Fashion Supply Chain Delay & Risk Monitor</h1>
          <p>Inditex-context dashboard built with real public brand information from Inditex and scenario-based operational records for portfolio demonstration.</p>
          <p>Brand names and public context are real. Purchase orders, delays, incidents, risks, milestones and mitigation actions are simulated operational scenarios, not internal Inditex data.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='note'><b>Portfolio pulse:</b> {len(data['collections'])} launches, {data['collections']['brand_name'].nunique()} brands, {data['collections']['market'].nunique()} markets and {data['purchase_orders']['supplier_id'].nunique()} active suppliers in the current view.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class='note data-disclaimer'>
        <b>Data note:</b> This dashboard uses real Inditex brands and public 2024 context for realism. The line-level operational data is synthetic and should be read as plausible PMO scenarios, not official company records.
        </div>
        """,
        unsafe_allow_html=True,
    )


def overview_tab(data: dict[str, pd.DataFrame], readiness: pd.DataFrame, kpis: dict[str, float], scorecard: pd.DataFrame) -> None:
    st.header("Executive Overview")
    cols = st.columns(4)
    with cols[0]:
        metric_card("Readiness score", f"{kpis['readiness_score']:.1f}", "Portfolio average, 0-100")
    with cols[1]:
        metric_card("Open critical risks", str(kpis["open_critical_risks"]), "Unresolved severe exposure")
    with cols[2]:
        metric_card("Blocked milestones", str(kpis["blocked_milestones_count"]), "Dependencies needing action")
    with cols[3]:
        metric_card("Average delay days", f"{kpis['average_delay_days']:.1f}", "Milestones and orders")
    cols = st.columns(4)
    with cols[0]:
        metric_card("Overdue actions", str(kpis["overdue_actions_count"]), "Mitigations past due")
    with cols[1]:
        metric_card("On-time milestone rate", pct(kpis["on_time_milestone_rate"]), "Completed milestones")
    with cols[2]:
        metric_card("Scope at risk", pct(kpis["scope_at_risk_pct"]), "SKU scope in At Risk/Critical")
    with cols[3]:
        metric_card("At-risk launches", str(kpis["at_risk_launches_count"]), "Collections below Watch")

    insight_card("Executive interpretation.", executive_text(data, readiness))

    collections = data["collections"].merge(
        readiness[["collection_id", "readiness_score", "readiness_band"]],
        on="collection_id",
        how="left",
        suffixes=("", "_current"),
    )
    collections["readiness_score"] = collections["readiness_score_current"].fillna(collections.get("readiness_score"))
    collections["readiness_band"] = collections["readiness_band_current"].fillna(collections.get("readiness_band"))
    collections = collections.sort_values("readiness_score")

    col1, col2 = st.columns([1.45, 1])
    with col1:
        fig = px.bar(
            collections,
            x="readiness_score",
            y="collection_name",
            color="readiness_band",
            orientation="h",
            title="Readiness by Collection",
            color_discrete_map=BAND_COLORS,
            custom_data=["brand_name", "market", "launch_date", "readiness_band", "readiness_score"],
            labels={"readiness_score": "Readiness score", "collection_name": "Collection", "readiness_band": "Readiness band"},
        )
        update_hover(
            fig,
            "<b>%{y}</b><br>Brand: %{customdata[0]}<br>Market: %{customdata[1]}<br>Launch: %{customdata[2]|%Y-%m-%d}<br>Readiness: %{customdata[4]:.1f}/100<br>Status: %{customdata[3]}<extra></extra>",
        )
        st.plotly_chart(apply_chart_theme(fig, height=520), width="stretch")
    with col2:
        status = collections["readiness_band"].value_counts().rename_axis("status").reset_index(name="launches")
        fig = px.pie(status, names="status", values="launches", title="Launch Portfolio Status", color="status", color_discrete_map=BAND_COLORS, hole=.58)
        fig.update_traces(textinfo="label+percent", hovertemplate="<b>%{label}</b><br>Launches: %{value}<br>Share: %{percent}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=520), width="stretch")

    selected = st.selectbox("Inspect collection", options=collections["collection_name"], key="inspect_collection")
    collection_detail_panel(collections[collections["collection_name"] == selected].iloc[0], data["milestones"], data["risks"], data["actions"], data["purchase_orders"])


def delay_tab(data: dict[str, pd.DataFrame]) -> None:
    st.header("Delay Monitoring")
    insight_card("Delay interpretation.", delay_text(data))
    if data["milestones"].empty or data["purchase_orders"].empty:
        st.warning("No delay data matches the current filters.")
        return

    col1, col2 = st.columns(2)
    with col1:
        delay_trend = (
            data["milestones"].assign(month=data["milestones"]["planned_date"].dt.to_period("M").dt.to_timestamp())
            .groupby("month", as_index=False)
            .agg(avg_delay=("delay_days", "mean"), blocked=("status", lambda s: (s == "Blocked").sum()))
        )
        fig = px.line(delay_trend, x="month", y="avg_delay", markers=True, title="Milestone Delay Trend", labels={"month": "Planned month", "avg_delay": "Average delay days"}, custom_data=["blocked"])
        update_hover(fig, "Month: %{x|%Y-%m}<br>Average Delay: %{y:.1f} days<br>Blocked Milestones: %{customdata[0]}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")
    with col2:
        workstream_delay = (
            data["milestones"].groupby("workstream", as_index=False)
            .agg(avg_delay=("delay_days", "mean"), blocked=("status", lambda s: (s == "Blocked").sum()))
            .sort_values("avg_delay", ascending=False)
        )
        workstream_delay["Workstream"] = workstream_delay["workstream"].map(pretty_label)
        fig = px.bar(workstream_delay, x="avg_delay", y="Workstream", orientation="h", title="Average Delay by Workstream", labels={"avg_delay": "Average delay days"}, custom_data=["blocked", "workstream"])
        update_hover(fig, "Workstream: %{y}<br>Average Delay: %{x:.1f} days<br>Blocked Milestones: %{customdata[0]}<br>PM Interpretation: Escalate if launch date is close<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.box(data["purchase_orders"], x="status", y="delay_days", color="status", title="Purchase Order Delay Distribution", labels={"status": "PO status", "delay_days": "Delay days"}, color_discrete_map=STATUS_COLORS)
        update_hover(fig, "PO Status: %{x}<br>Delay: %{y:.1f} days<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")
    with col2:
        by_collection = data["milestones"].groupby("collection_name", as_index=False).agg(total_delay=("delay_days", "sum"), blocked=("status", lambda s: (s == "Blocked").sum())).sort_values("total_delay", ascending=False).head(12)
        fig = px.bar(by_collection, x="total_delay", y="collection_name", orientation="h", title="Collections with Highest Slippage", labels={"total_delay": "Total delay days", "collection_name": "Collection"}, custom_data=["blocked"])
        update_hover(fig, "Collection: %{y}<br>Total Delay: %{x:.1f} days<br>Blocked Milestones: %{customdata[0]}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")

    delayed = data["purchase_orders"].sort_values("delay_days", ascending=False).head(25)
    table = clean_table(
        delayed,
        ["po_id", "collection_name", "supplier_name", "sku_family", "transport_mode", "destination_hub", "planned_arrival_date", "actual_arrival_date", "status", "delay_days", "lead_time_variance_days"],
        {
            "po_id": "PO",
            "collection_name": "Collection",
            "supplier_name": "Supplier",
            "sku_family": "SKU Family",
            "transport_mode": "Mode",
            "destination_hub": "Destination Hub",
            "planned_arrival_date": "Planned Arrival",
            "actual_arrival_date": "Actual Arrival",
            "status": "Status",
            "delay_days": "Delay",
            "lead_time_variance_days": "Lead-Time Variance",
        },
        date_cols=["planned_arrival_date", "actual_arrival_date"],
        day_cols=["delay_days", "lead_time_variance_days"],
    )
    render_business_table(table)


def risk_tab(data: dict[str, pd.DataFrame]) -> None:
    st.header("Risk Monitoring")
    insight_card("Risk interpretation.", risk_text(data))
    if data["risks"].empty:
        st.warning("No risk data matches the current filters.")
        return

    risks = data["risks"].copy()
    risks["Workstream"] = risks["workstream"].map(pretty_label)
    col1, col2 = st.columns([1.25, 1])
    with col1:
        fig = px.scatter(
            risks,
            x="probability",
            y="impact",
            size="risk_score",
            color="severity",
            title="Risk Matrix",
            color_discrete_map=SEVERITY_COLORS,
            custom_data=["risk_type", "collection_name", "Workstream", "risk_score", "owner", "status", "target_resolution_date", "risk_description"],
            labels={"probability": "Probability", "impact": "Impact", "severity": "Severity"},
        )
        update_hover(
            fig,
            "<b>%{customdata[0]}</b><br>Collection: %{customdata[1]}<br>Workstream: %{customdata[2]}<br>Probability: %{x}/5<br>Impact: %{y}/5<br>Risk Score: %{customdata[3]:.1f}<br>Owner: %{customdata[4]}<br>Status: %{customdata[5]}<br>Target Resolution: %{customdata[6]|%Y-%m-%d}<br>Recommended Action: Validate mitigation owner and next decision gate<extra></extra>",
        )
        fig.update_xaxes(dtick=1, range=[0.5, 5.5])
        fig.update_yaxes(dtick=1, range=[0.5, 5.5])
        st.plotly_chart(apply_chart_theme(fig, height=500), width="stretch")
    with col2:
        severity_counts = risks["severity"].value_counts().reindex(SEVERITY_ORDER).dropna().rename_axis("Severity").reset_index(name="Risks")
        fig = px.bar(severity_counts, x="Severity", y="Risks", color="Severity", title="Risks by Severity", color_discrete_map=SEVERITY_COLORS, category_orders={"Severity": SEVERITY_ORDER})
        update_hover(fig, "Severity: %{x}<br>Risks: %{y}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=500), width="stretch")

    exposure = risk_exposure_by_workstream(risks)
    if not exposure.empty:
        exposure["Workstream"] = exposure["workstream"].map(pretty_label)
        fig = px.bar(exposure, x="risk_exposure", y="Workstream", orientation="h", title="Open Risk Exposure by Workstream", labels={"risk_exposure": "Risk exposure"}, custom_data=["open_risks", "critical_risks"])
        update_hover(fig, "Workstream: %{y}<br>Risk Exposure: %{x:.1f}<br>Open Risks: %{customdata[0]}<br>Critical Risks: %{customdata[1]}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")

    open_risks = risks[risks["is_open"]].copy()
    open_risks["severity_order"] = open_risks["severity"].map({v: i for i, v in enumerate(SEVERITY_ORDER)})
    open_risks = open_risks.sort_values(["severity_order", "risk_score"], ascending=[True, False]).head(30)
    table = clean_table(
        open_risks,
        ["risk_id", "collection_name", "Workstream", "risk_type", "severity", "risk_score", "owner", "status", "target_resolution_date"],
        {"risk_id": "Risk", "collection_name": "Collection", "risk_type": "Risk Type", "severity": "Severity", "risk_score": "Score", "owner": "Owner", "status": "Status", "target_resolution_date": "Target Resolution"},
        date_cols=["target_resolution_date"],
        score_cols=["risk_score"],
    )
    render_business_table(table)


def supplier_tab(data: dict[str, pd.DataFrame], scorecard: pd.DataFrame) -> None:
    st.header("Supplier Performance")
    insight_card("Supplier interpretation.", supplier_text(scorecard))
    if scorecard.empty:
        st.warning("No supplier data matches the current filters.")
        return

    cols = st.columns(4)
    with cols[0]:
        metric_card("Active suppliers", str(scorecard["supplier_id"].nunique()), "Filtered sourcing base")
    with cols[1]:
        metric_card("Critical watchlist", str((scorecard["supplier_risk_band"] == "Critical Watchlist").sum()), "Needs sourcing review")
    with cols[2]:
        metric_card("Avg supplier delay", f"{scorecard['avg_delay'].mean():.1f}", "Days across active suppliers")
    with cols[3]:
        metric_card("Avg reliability", f"{scorecard['reliability_score_base'].mean():.1f}", "Supplier base score")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.scatter(
            scorecard,
            x="reliability_score_base",
            y="avg_delay",
            size="incidents",
            color="supplier_risk_band",
            title="Reliability vs Delay",
            color_discrete_map=SUPPLIER_BAND_COLORS,
            custom_data=["supplier_name", "country", "lead_time_variance", "incidents", "main_sku_family", "suggested_pm_action"],
            labels={"reliability_score_base": "Reliability score", "avg_delay": "Average PO delay", "supplier_risk_band": "Supplier risk band"},
        )
        update_hover(fig, "Supplier: %{customdata[0]}<br>Country: %{customdata[1]}<br>Average PO Delay: %{y:.1f} days<br>Lead-Time Variance: %{customdata[2]:+.1f} days<br>Incidents: %{customdata[3]}<br>Reliability: %{x:.1f}/100<br>Main SKU Family: %{customdata[4]}<br>PM Action: %{customdata[5]}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=470), width="stretch")
    with col2:
        incident_breakdown = data["incidents"].groupby("issue_type", as_index=False).size().sort_values("size", ascending=False).head(10)
        fig = px.bar(incident_breakdown, x="size", y="issue_type", orientation="h", title="Incident Type Breakdown", labels={"size": "Incidents", "issue_type": "Incident type"})
        update_hover(fig, "Incident Type: %{y}<br>Incidents: %{x}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=470), width="stretch")

    watchlist = scorecard.head(15)
    table = clean_table(
        watchlist,
        ["supplier_name", "supplier_city", "country", "avg_delay", "lead_time_variance", "incidents", "reliability_score_base", "supplier_risk_band", "suggested_pm_action"],
        {"supplier_name": "Supplier", "supplier_city": "City", "country": "Country", "avg_delay": "Avg Delay", "lead_time_variance": "Lead-Time Variance", "incidents": "Incidents", "reliability_score_base": "Reliability", "supplier_risk_band": "Risk Band", "suggested_pm_action": "Suggested PM Action"},
        day_cols=["avg_delay", "lead_time_variance"],
        score_cols=["reliability_score_base"],
    )
    render_business_table(table)


def geography_tab(data: dict[str, pd.DataFrame], scorecard: pd.DataFrame) -> None:
    st.header("Supply Chain Geography")
    insight_card("Geography interpretation.", "The map connects sourcing geography with launch execution risk. Locations with both repeated incidents and high delay variance should be discussed in the weekly sourcing and logistics review.")
    if scorecard.empty or "supplier_lat" not in scorecard.columns:
        st.warning("Supplier location data is not available. Regenerate and transform the dataset.")
        return

    map_data = scorecard.dropna(subset=["supplier_lat", "supplier_lon"]).copy()
    map_data["marker_size"] = map_data["incidents"].clip(lower=1) + map_data["order_volume"].clip(0, 20) / 3
    col1, col2 = st.columns([1.5, 1])
    with col1:
        fig = px.scatter_mapbox(
            map_data,
            lat="supplier_lat",
            lon="supplier_lon",
            size="marker_size",
            color="supplier_risk_band",
            color_discrete_map=SUPPLIER_BAND_COLORS,
            hover_name="supplier_name",
            custom_data=["supplier_city", "country", "supplier_risk_band", "avg_delay", "incidents", "reliability_score_base"],
            zoom=1.35,
            height=600,
            title="Supplier Locations and Operational Exposure",
            labels={"supplier_risk_band": "Supplier risk band"},
        )
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox=dict(center=dict(lat=28, lon=28), zoom=1.35),
            dragmode="pan",
            margin=dict(l=8, r=8, t=82, b=18),
        )
        fig.update_traces(
            marker=dict(opacity=0.86),
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "%{customdata[0]}, %{customdata[1]}<br>"
                "Risk band: %{customdata[2]}<br>"
                "Avg delay: %{customdata[3]:.1f} days<br>"
                "Incidents: %{customdata[4]:.0f}<br>"
                "Reliability: %{customdata[5]:.1f}/100"
                "<extra></extra>"
            ),
        )
        st.plotly_chart(apply_chart_theme(fig, height=600), width="stretch", config={"scrollZoom": True, "displayModeBar": False})
    with col2:
        top_locations = map_data.sort_values("supplier_risk_score", ascending=False).head(10)
        table = clean_table(
            top_locations,
            ["supplier_name", "supplier_city", "country", "avg_delay", "incidents", "reliability_score_base", "supplier_risk_band", "suggested_pm_action"],
            {"supplier_name": "Supplier", "supplier_city": "City", "country": "Country", "avg_delay": "Avg Delay", "incidents": "Incidents", "reliability_score_base": "Reliability", "supplier_risk_band": "Risk Level", "suggested_pm_action": "Suggested PM Action"},
            day_cols=["avg_delay"],
            score_cols=["reliability_score_base"],
        )
        render_business_table(table, height=300)
        selected_supplier = st.selectbox("Inspect supplier", map_data["supplier_name"].tolist(), key="inspect_supplier")
        supplier_detail_panel(map_data[map_data["supplier_name"] == selected_supplier].iloc[0], data["risks"], data["actions"], data["incidents"])


def timeline_tab(data: dict[str, pd.DataFrame]) -> None:
    st.header("Launch Timeline")
    insight_card("Timeline interpretation.", "Timeline monitoring matters because launch readiness is a chain of decisions, not a final checklist. Planned vs actual milestone movement shows where governance confidence is being created or lost.")
    if data["milestones"].empty:
        st.warning("No milestone data matches the active filters.")
        return

    collection_options = sorted(data["milestones"]["collection_name"].dropna().unique())
    selected = st.multiselect("Timeline collections", collection_options, default=collection_options[: min(5, len(collection_options))])
    timeline = data["milestones"][data["milestones"]["collection_name"].isin(selected)].copy() if selected else data["milestones"].copy()
    timeline["end_date"] = timeline["actual_date"].fillna(timeline["planned_date"] + pd.to_timedelta(timeline["delay_days"].clip(lower=1), unit="D"))
    timeline["Workstream"] = timeline["workstream"].map(pretty_label)
    timeline["Task"] = timeline["collection_name"] + " | " + timeline["milestone_name"]
    fig = px.timeline(
        timeline.sort_values(["launch_date", "planned_date"]),
        x_start="planned_date",
        x_end="end_date",
        y="Task",
        color="status",
        title="Launch Timeline: Planned Gate to Current / Actual Completion",
        color_discrete_map=STATUS_COLORS,
        custom_data=["collection_name", "Workstream", "milestone_name", "planned_date", "actual_date", "status", "delay_days", "owner", "blocker_reason"],
    )
    update_hover(fig, "Collection: %{customdata[0]}<br>Workstream: %{customdata[1]}<br>Milestone: %{customdata[2]}<br>Planned: %{customdata[3]|%Y-%m-%d}<br>Actual/Current: %{customdata[4]|%Y-%m-%d}<br>Status: %{customdata[5]}<br>Delay: %{customdata[6]:.1f} days<br>Owner: %{customdata[7]}<br>Blocker: %{customdata[8]}<extra></extra>")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(apply_chart_theme(fig, height=max(520, min(900, 38 * len(timeline)))), width="stretch")


def dependencies_tab(data: dict[str, pd.DataFrame]) -> None:
    st.header("Dependency Tracker")
    insight_card("Dependency interpretation.", dependency_text(data))
    milestones = data["milestones"].copy()
    if milestones.empty:
        st.warning("No dependency data matches the active filters.")
        return

    deps = milestones.dropna(subset=["dependency_id"]).merge(
        milestones[["milestone_id", "milestone_name", "workstream", "owner", "status", "delay_days", "blocker_reason"]],
        left_on="dependency_id",
        right_on="milestone_id",
        suffixes=("_downstream", "_upstream"),
        how="left",
    )
    deps["delay_propagation_days"] = deps["delay_days_upstream"].fillna(0) + deps["delay_days_downstream"].fillna(0)
    deps["recommended_escalation_action"] = deps.apply(
        lambda r: "Escalate owner handoff before launch governance" if r["status_upstream"] in ["Blocked", "Delayed", "At Risk"] or r["status_downstream"] == "Blocked" else "Monitor in weekly PMO review",
        axis=1,
    )

    col1, col2 = st.columns(2)
    with col1:
        affected = milestones[milestones["status"].eq("Blocked")].groupby("collection_name", as_index=False).size().sort_values("size", ascending=False)
        fig = px.bar(affected, x="size", y="collection_name", orientation="h", title="Collections Most Affected by Blockers", labels={"size": "Blocked milestones", "collection_name": "Collection"})
        update_hover(fig, "Collection: %{y}<br>Blocked Milestones: %{x}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")
    with col2:
        heat = pd.crosstab(milestones["workstream"].map(pretty_label), milestones["status"])
        fig = px.imshow(heat, text_auto=True, title="Workstream Status Heatmap", color_continuous_scale=["#f7fafc", "#9fc7c9", "#2f6f73"], labels=dict(x="Status", y="Workstream", color="Milestones"))
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")

    chain = deps.sort_values("delay_propagation_days", ascending=False).head(30)
    table = clean_table(
        chain,
        ["collection_name", "milestone_name_upstream", "workstream_upstream", "owner_upstream", "status_upstream", "milestone_name_downstream", "workstream_downstream", "owner_downstream", "status_downstream", "delay_propagation_days", "blocker_reason_downstream", "recommended_escalation_action"],
        {
            "collection_name": "Collection",
            "milestone_name_upstream": "Upstream Milestone",
            "workstream_upstream": "Upstream Workstream",
            "owner_upstream": "Upstream Owner",
            "status_upstream": "Upstream Status",
            "milestone_name_downstream": "Downstream Milestone",
            "workstream_downstream": "Downstream Workstream",
            "owner_downstream": "Downstream Owner",
            "status_downstream": "Downstream Status",
            "delay_propagation_days": "Delay Propagation",
            "blocker_reason_downstream": "Blocker Reason",
            "recommended_escalation_action": "Recommended Escalation",
        },
        day_cols=["delay_propagation_days"],
    )
    render_business_table(table, height=460)


def actions_tab(data: dict[str, pd.DataFrame]) -> None:
    st.header("Actions & Mitigation Board")
    overdue = int(data["actions"]["is_overdue"].sum()) if not data["actions"].empty else 0
    insight_card("Actions interpretation.", f"The mitigation board should answer who needs to act this week. {overdue} overdue actions are visible in the current view; overdue items tied to high or critical risks should appear first.")
    if data["actions"].empty:
        st.warning("No action data matches the active filters.")
        return

    actions = data["actions"].copy()
    actions["priority_order"] = actions["priority"].map({v: i for i, v in enumerate(PRIORITY_ORDER)})
    actions["Priority"] = pd.Categorical(actions["priority"], categories=PRIORITY_ORDER, ordered=True)

    col1, col2 = st.columns(2)
    with col1:
        action_counts = actions.groupby(["Priority", "status"], observed=False).size().reset_index(name="actions")
        fig = px.bar(action_counts, x="Priority", y="actions", color="status", title="Actions by Priority and Status", labels={"actions": "Actions", "status": "Status"}, category_orders={"Priority": PRIORITY_ORDER})
        update_hover(fig, "Priority: %{x}<br>Status: %{fullData.name}<br>Actions: %{y}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")
    with col2:
        owner_actions = actions[actions["status"] != "Completed"].groupby("owner", as_index=False).size().sort_values("size", ascending=False).head(12)
        fig = px.bar(owner_actions, x="size", y="owner", orientation="h", title="Open Actions by Owner", labels={"size": "Open actions", "owner": "Owner"})
        update_hover(fig, "Owner: %{y}<br>Open Actions: %{x}<extra></extra>")
        st.plotly_chart(apply_chart_theme(fig, height=430), width="stretch")

    actions["Action Timing"] = actions["is_overdue"].map(lambda x: "Overdue" if x else "On track")
    actions = actions.sort_values(["is_overdue", "priority_order", "due_date"], ascending=[False, True, True]).head(35)
    table = clean_table(
        actions,
        ["action_id", "collection_name", "risk_type", "severity", "action_type", "owner", "due_date", "status", "priority", "expected_impact", "Action Timing"],
        {"action_id": "Action", "collection_name": "Collection", "risk_type": "Risk Type", "severity": "Severity", "action_type": "Action Type", "owner": "Owner", "due_date": "Due Date", "status": "Status", "priority": "Priority", "expected_impact": "Expected Impact"},
        date_cols=["due_date"],
    )
    render_business_table(table, height=460)


def scenario_tab(data: dict[str, pd.DataFrame], readiness: pd.DataFrame, kpis: dict[str, float], scorecard: pd.DataFrame) -> None:
    st.header("Scenario Simulator")
    insight_card("Scenario simulator - illustrative PMO decision support.", "These controls are not a forecast model. They show directional impact from plausible PMO decisions so the dashboard can support discussion in a launch review.")
    col1, col2 = st.columns(2)
    with col1:
        expedite = st.checkbox("Assume expedited freight for delayed logistics POs", value=True)
        close_actions = st.checkbox("Assume overdue critical actions are completed", value=True)
    with col2:
        supplier_support = st.checkbox("Assume top supplier watchlist receives mitigation support", value=False)
        partial_launch = st.checkbox("Assume partial launch approval for low-risk delayed SKUs", value=False)

    adjusted = kpis.copy()
    risk_exposure = data["risks"].loc[data["risks"]["is_open"], "risk_score"].sum() if not data["risks"].empty else 0
    if expedite:
        adjusted["average_delay_days"] = max(0, adjusted["average_delay_days"] - 1.4)
        adjusted["readiness_score"] = min(100, adjusted["readiness_score"] + 3.0)
    if close_actions:
        adjusted["overdue_actions_count"] = max(0, adjusted["overdue_actions_count"] - int(data["actions"]["is_overdue"].sum()))
        adjusted["readiness_score"] = min(100, adjusted["readiness_score"] + 4.5)
        risk_exposure *= 0.88
    if supplier_support and not scorecard.empty:
        adjusted["average_delay_days"] = max(0, adjusted["average_delay_days"] - 0.9)
        adjusted["readiness_score"] = min(100, adjusted["readiness_score"] + 2.5)
        risk_exposure *= 0.92
    if partial_launch:
        adjusted["scope_at_risk_pct"] = max(0, adjusted["scope_at_risk_pct"] - 0.06)
        adjusted["at_risk_launches_count"] = max(0, adjusted["at_risk_launches_count"] - 1)

    cols = st.columns(5)
    with cols[0]:
        metric_card("Readiness impact", f"{adjusted['readiness_score']:.1f}", f"Base {kpis['readiness_score']:.1f}")
    with cols[1]:
        metric_card("At-risk launches", str(adjusted["at_risk_launches_count"]), f"Base {kpis['at_risk_launches_count']}")
    with cols[2]:
        metric_card("Average delay", f"{adjusted['average_delay_days']:.1f}", f"Base {kpis['average_delay_days']:.1f}")
    with cols[3]:
        metric_card("Risk exposure", f"{risk_exposure:.1f}", "Open risk score")
    with cols[4]:
        metric_card("Scope at risk", pct(adjusted["scope_at_risk_pct"]), f"Base {pct(kpis['scope_at_risk_pct'])}")

    with st.expander("KPI Methodology", expanded=False):
        st.markdown(
            """
            - **Readiness score:** starts at 100, then subtracts for open critical risks, blocked milestones, overdue actions, delay severity, supplier reliability and launch proximity. Completed milestones and closed mitigations add small positive credit.
            - **Risk score:** probability x impact, grouped into Low, Medium, High and Critical.
            - **Supplier risk band:** combines average delay, lead-time variance, incident count, reliability gap and open critical risks linked to supplier collections.
            - **Scope at risk:** share of planned SKU scope attached to At Risk or Critical launches.
            - **On-time milestone rate:** completed milestones with no positive delay divided by all completed milestones.
            - **Mitigation closure rate:** completed mitigation actions divided by all mitigation actions in the filtered view.
            """
        )


def portfolio_story_tab(data: dict[str, pd.DataFrame], scorecard: pd.DataFrame, kpis: dict[str, float]) -> None:
    st.header("Portfolio Story / Project Management Insights")
    worst_workstream = data["milestones"].groupby("workstream")["delay_days"].sum().sort_values(ascending=False).index[0] if not data["milestones"].empty else "the active workstreams"
    worst_supplier = scorecard.iloc[0]["supplier_name"] if not scorecard.empty else "the highest-variance supplier"
    worst_collection = data["collections"].sort_values("readiness_score").iloc[0]["collection_name"] if not data["collections"].empty and "readiness_score" in data["collections"] else "the lowest-readiness collection"
    st.markdown(
        f"""
        <div class="insight">
        <b>PMO escalation view.</b> Escalate {worst_collection} first because it carries the weakest readiness signal in the filtered portfolio.
        The most urgent operating lane is {pretty_label(worst_workstream)}, where delay and dependency pressure are most visible.
        Supplier review should start with {worst_supplier}. The mitigation board has {kpis['overdue_actions_count']} overdue actions; clearing those items should be treated as a launch governance priority before approving final go-live.
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    load_css()
    try:
        raw_data = get_data()
    except FileNotFoundError:
        st.error("Processed data was not found. Run `python src/generate_data.py` and `python src/transform_data.py` from the project root.")
        return

    data, active_filters = sidebar_filters(raw_data)
    if data["collections"].empty:
        st.warning("No records match the current filters. Reset or widen the selection to restore the portfolio view.")
        return

    readiness = calculate_readiness_scores(data["collections"], data["milestones"], data["risks"], data["actions"], data["purchase_orders"], data["suppliers"], REFERENCE_DATE)
    kpis = portfolio_kpis(data["collections"], data["milestones"], data["risks"], data["actions"], data["purchase_orders"], data["suppliers"], REFERENCE_DATE)
    scorecard = build_scorecard(data)

    hero(data)
    filter_chips(active_filters)

    tabs = st.tabs(["Overview", "Delay", "Risk", "Suppliers", "Geography", "Timeline", "Dependencies", "Actions", "Scenario", "Story"])
    with tabs[0]:
        overview_tab(data, readiness, kpis, scorecard)
    with tabs[1]:
        delay_tab(data)
    with tabs[2]:
        risk_tab(data)
    with tabs[3]:
        supplier_tab(data, scorecard)
    with tabs[4]:
        geography_tab(data, scorecard)
    with tabs[5]:
        timeline_tab(data)
    with tabs[6]:
        dependencies_tab(data)
    with tabs[7]:
        actions_tab(data)
    with tabs[8]:
        scenario_tab(data, readiness, kpis, scorecard)
    with tabs[9]:
        portfolio_story_tab(data, scorecard, kpis)


if __name__ == "__main__":
    main()
