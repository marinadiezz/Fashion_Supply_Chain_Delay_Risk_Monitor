from __future__ import annotations

import pandas as pd

from risk_scoring import calculate_readiness_scores
from utils import safe_divide


REFERENCE_DATE = pd.Timestamp("2026-04-25")


def on_time_milestone_rate(milestones: pd.DataFrame) -> float:
    completed = milestones[milestones["status"] == "Completed"]
    if completed.empty:
        return 0.0
    return float((completed["delay_days"].fillna(0) <= 0).mean())


def average_delay_days(*frames: pd.DataFrame) -> float:
    values = []
    for frame in frames:
        if frame is not None and "delay_days" in frame.columns and not frame.empty:
            values.extend(frame["delay_days"].fillna(0).clip(lower=0).tolist())
    return round(float(pd.Series(values).mean()), 1) if values else 0.0


def overdue_actions_count(actions: pd.DataFrame, reference_date: pd.Timestamp = REFERENCE_DATE) -> int:
    if actions.empty:
        return 0
    return int(((actions["status"] != "Completed") & (pd.to_datetime(actions["due_date"]) < reference_date)).sum())


def due_soon_actions_count(actions: pd.DataFrame, reference_date: pd.Timestamp = REFERENCE_DATE, days: int = 14) -> int:
    if actions.empty:
        return 0
    due = pd.to_datetime(actions["due_date"])
    return int(((actions["status"] != "Completed") & (due >= reference_date) & (due <= reference_date + pd.Timedelta(days=days))).sum())


def open_critical_risks(risks: pd.DataFrame) -> int:
    if risks.empty:
        return 0
    return int(((risks["severity"] == "Critical") & (~risks["status"].isin(["Closed", "Resolved"]))).sum())


def supplier_reliability_score(purchase_orders: pd.DataFrame, suppliers: pd.DataFrame) -> float:
    if purchase_orders.empty or suppliers.empty:
        return 0.0
    if "reliability_score_base" in purchase_orders.columns:
        merged = purchase_orders.copy()
    else:
        merged = purchase_orders.merge(suppliers[["supplier_id", "reliability_score_base"]], on="supplier_id", how="left")
    weights = merged["quantity"].fillna(1).clip(lower=1)
    return round(float((merged["reliability_score_base"] * weights).sum() / weights.sum()), 1)


def mitigation_closure_rate(actions: pd.DataFrame) -> float:
    if actions.empty:
        return 0.0
    return float(actions["status"].eq("Completed").mean())


def scope_at_risk_pct(collections: pd.DataFrame, readiness: pd.DataFrame) -> float:
    if collections.empty or readiness.empty:
        return 0.0
    if "readiness_band" in collections.columns:
        merged = collections.copy()
    else:
        merged = collections.merge(readiness[["collection_id", "readiness_band"]], on="collection_id", how="left")
    scope = merged["planned_scope_skus"].sum()
    risk_scope = merged.loc[merged["readiness_band"].isin(["At Risk", "Critical"]), "planned_scope_skus"].sum()
    return safe_divide(risk_scope, scope)


def blocked_milestones_count(milestones: pd.DataFrame) -> int:
    if milestones.empty:
        return 0
    return int(milestones["status"].eq("Blocked").sum())


def lead_time_variance(purchase_orders: pd.DataFrame) -> float:
    if purchase_orders.empty:
        return 0.0
    return round(float(purchase_orders["lead_time_variance_days"].fillna(0).mean()), 1)


def delayed_purchase_orders_count(purchase_orders: pd.DataFrame) -> int:
    if purchase_orders.empty:
        return 0
    return int(purchase_orders["delay_days"].fillna(0).gt(0).sum())


def high_risk_collections_count(readiness: pd.DataFrame) -> int:
    if readiness.empty:
        return 0
    return int(readiness["readiness_band"].isin(["At Risk", "Critical"]).sum())


def launch_countdown_days(collections: pd.DataFrame, reference_date: pd.Timestamp = REFERENCE_DATE) -> int:
    if collections.empty:
        return 0
    future = pd.to_datetime(collections["launch_date"]) - reference_date
    future = future.dt.days
    future = future[future >= 0]
    return int(future.min()) if not future.empty else 0


def at_risk_launches_count(readiness: pd.DataFrame) -> int:
    return high_risk_collections_count(readiness)


def classify_supplier_risk(score: float) -> str:
    if score >= 70:
        return "Critical Watchlist"
    if score >= 50:
        return "High Variance"
    if score >= 30:
        return "Monitor"
    return "Low Risk"


def supplier_pm_action(risk_band: str) -> str:
    actions = {
        "Critical Watchlist": "Escalate contingency plan and confirm alternative capacity",
        "High Variance": "Review weekly recovery plan with sourcing and logistics",
        "Monitor": "Track next shipment gate and validate documentation",
        "Low Risk": "Keep standard launch governance cadence",
    }
    return actions.get(risk_band, "Review supplier status")


def supplier_scorecard(
    purchase_orders: pd.DataFrame,
    suppliers: pd.DataFrame,
    incidents: pd.DataFrame | None = None,
    risks: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if purchase_orders.empty:
        return pd.DataFrame()

    group_cols = ["supplier_id", "supplier_name", "country", "region"]
    optional_cols = [
        "supplier_city",
        "supplier_lat",
        "supplier_lon",
        "supplier_specialty",
        "reliability_score_base",
        "capacity_band",
        "escalation_level",
    ]
    group_cols.extend([c for c in optional_cols if c in purchase_orders.columns])

    scorecard = (
        purchase_orders.groupby(group_cols, dropna=False)
        .agg(
            avg_delay=("delay_days", "mean"),
            lead_time_variance=("lead_time_variance_days", "mean"),
            order_volume=("po_id", "count"),
            total_units=("quantity", "sum"),
            linked_collections=("collection_name", lambda s: ", ".join(sorted(s.dropna().unique())[:4])),
            main_sku_family=("sku_family", lambda s: s.mode().iat[0] if not s.mode().empty else "mixed"),
            destination_market=("destination_market", lambda s: ", ".join(sorted(s.dropna().unique())[:3]) if "destination_market" in purchase_orders.columns else ""),
            destination_hub=("destination_hub", lambda s: ", ".join(sorted(s.dropna().unique())[:3]) if "destination_hub" in purchase_orders.columns else ""),
            transport_mode=("transport_mode", lambda s: s.mode().iat[0] if "transport_mode" in purchase_orders.columns and not s.mode().empty else ""),
            route_risk_score=("route_risk_score", "mean") if "route_risk_score" in purchase_orders.columns else ("delay_days", "mean"),
            avg_route_delay_days=("avg_route_delay_days", "mean") if "avg_route_delay_days" in purchase_orders.columns else ("delay_days", "mean"),
        )
        .reset_index()
    )

    if "reliability_score_base" not in scorecard.columns and not suppliers.empty:
        scorecard = scorecard.merge(
            suppliers[["supplier_id", "reliability_score_base"]],
            on="supplier_id",
            how="left",
        )

    if incidents is not None and not incidents.empty:
        incident_summary = (
            incidents.groupby("supplier_id")
            .agg(
                incidents=("incident_id", "count"),
                open_incidents=("status", lambda s: s.isin(["Open", "In Review"]).sum()),
                main_incident_type=("issue_type", lambda s: s.mode().iat[0] if not s.mode().empty else "None"),
            )
            .reset_index()
        )
        scorecard = scorecard.merge(incident_summary, on="supplier_id", how="left")
    else:
        scorecard["incidents"] = 0
        scorecard["open_incidents"] = 0
        scorecard["main_incident_type"] = "None"

    scorecard[["incidents", "open_incidents"]] = scorecard[["incidents", "open_incidents"]].fillna(0)
    scorecard["main_incident_type"] = scorecard["main_incident_type"].fillna("None")

    if risks is not None and not risks.empty and "collection_id" in purchase_orders.columns:
        supplier_collections = purchase_orders[["supplier_id", "collection_id"]].drop_duplicates()
        linked_risks = supplier_collections.merge(
            risks[["collection_id", "risk_id", "severity", "is_open"]],
            on="collection_id",
            how="left",
        )
        risk_counts = (
            linked_risks[linked_risks["is_open"].fillna(False)]
            .groupby("supplier_id")
            .agg(
                open_linked_risks=("risk_id", "nunique"),
                open_critical_risks=("severity", lambda s: (s == "Critical").sum()),
            )
            .reset_index()
        )
        scorecard = scorecard.merge(risk_counts, on="supplier_id", how="left")
    else:
        scorecard["open_linked_risks"] = 0
        scorecard["open_critical_risks"] = 0

    scorecard[["open_linked_risks", "open_critical_risks"]] = scorecard[["open_linked_risks", "open_critical_risks"]].fillna(0)
    reliability_gap = (100 - scorecard["reliability_score_base"].fillna(80)).clip(lower=0)
    scorecard["supplier_risk_score"] = (
        scorecard["avg_delay"].clip(0, 25) * 1.4
        + scorecard["lead_time_variance"].clip(lower=0, upper=25) * 1.2
        + scorecard["incidents"].clip(0, 12) * 3.2
        + reliability_gap * 0.55
        + scorecard["open_critical_risks"].clip(0, 5) * 5
    ).round(1)
    scorecard["supplier_risk_band"] = scorecard["supplier_risk_score"].apply(classify_supplier_risk)
    scorecard["suggested_pm_action"] = scorecard["supplier_risk_band"].apply(supplier_pm_action)
    return scorecard.sort_values("supplier_risk_score", ascending=False)


def portfolio_kpis(
    collections: pd.DataFrame,
    milestones: pd.DataFrame,
    risks: pd.DataFrame,
    actions: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    suppliers: pd.DataFrame,
    reference_date: pd.Timestamp = REFERENCE_DATE,
) -> dict[str, float]:
    readiness = calculate_readiness_scores(collections, milestones, risks, actions, purchase_orders, suppliers, reference_date)
    return {
        "readiness_score": round(float(readiness["readiness_score"].mean()), 1) if not readiness.empty else 0.0,
        "on_time_milestone_rate": on_time_milestone_rate(milestones),
        "average_delay_days": average_delay_days(milestones, purchase_orders),
        "overdue_actions_count": overdue_actions_count(actions, reference_date),
        "due_soon_actions_count": due_soon_actions_count(actions, reference_date),
        "open_critical_risks": open_critical_risks(risks),
        "supplier_reliability_score": supplier_reliability_score(purchase_orders, suppliers),
        "mitigation_closure_rate": mitigation_closure_rate(actions),
        "scope_at_risk_pct": scope_at_risk_pct(collections, readiness),
        "blocked_milestones_count": blocked_milestones_count(milestones),
        "lead_time_variance": lead_time_variance(purchase_orders),
        "delayed_purchase_orders_count": delayed_purchase_orders_count(purchase_orders),
        "high_risk_collections_count": high_risk_collections_count(readiness),
        "launch_countdown_days": launch_countdown_days(collections, reference_date),
        "at_risk_launches_count": at_risk_launches_count(readiness),
    }
