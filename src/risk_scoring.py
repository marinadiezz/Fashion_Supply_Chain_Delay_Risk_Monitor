from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_risk_score(probability: float, impact: float) -> float:
    return round(float(probability) * float(impact), 2)


def classify_severity(score: float) -> str:
    if score >= 16:
        return "Critical"
    if score >= 10:
        return "High"
    if score >= 5:
        return "Medium"
    return "Low"


def add_risk_scoring(risks: pd.DataFrame) -> pd.DataFrame:
    df = risks.copy()
    df["risk_score"] = (df["probability"] * df["impact"]).round(2)
    df["severity"] = df["risk_score"].apply(classify_severity)
    df["is_open_critical"] = (df["severity"].eq("Critical")) & (~df["status"].isin(["Closed", "Resolved"]))
    return df


def risk_exposure_by_collection(risks: pd.DataFrame) -> pd.DataFrame:
    open_risks = risks[~risks["status"].isin(["Closed", "Resolved"])].copy()
    if open_risks.empty:
        return pd.DataFrame(columns=["collection_id", "risk_exposure", "open_risks", "critical_risks"])
    return (
        open_risks.groupby("collection_id")
        .agg(
            risk_exposure=("risk_score", "sum"),
            open_risks=("risk_id", "count"),
            critical_risks=("severity", lambda s: (s == "Critical").sum()),
        )
        .reset_index()
    )


def risk_exposure_by_workstream(risks: pd.DataFrame) -> pd.DataFrame:
    open_risks = risks[~risks["status"].isin(["Closed", "Resolved"])].copy()
    if open_risks.empty:
        return pd.DataFrame(columns=["workstream", "risk_exposure", "open_risks", "critical_risks"])
    return (
        open_risks.groupby("workstream")
        .agg(
            risk_exposure=("risk_score", "sum"),
            open_risks=("risk_id", "count"),
            critical_risks=("severity", lambda s: (s == "Critical").sum()),
        )
        .reset_index()
        .sort_values("risk_exposure", ascending=False)
    )


def calculate_readiness_scores(
    collections: pd.DataFrame,
    milestones: pd.DataFrame,
    risks: pd.DataFrame,
    actions: pd.DataFrame,
    purchase_orders: pd.DataFrame,
    suppliers: pd.DataFrame,
    reference_date: str | pd.Timestamp = "2026-04-25",
) -> pd.DataFrame:
    reference = pd.to_datetime(reference_date)
    rows = []

    if "reliability_score_base" in purchase_orders.columns:
        po_supplier = purchase_orders.copy()
    else:
        po_supplier = purchase_orders.merge(
            suppliers[["supplier_id", "reliability_score_base"]],
            on="supplier_id",
            how="left",
        )

    for _, collection in collections.iterrows():
        collection_id = collection["collection_id"]
        m = milestones[milestones["collection_id"] == collection_id]
        r = risks[risks["collection_id"] == collection_id]
        a = actions[actions["collection_id"] == collection_id]
        p = po_supplier[po_supplier["collection_id"] == collection_id]

        completed_rate = (m["status"] == "Completed").mean() if len(m) else 0
        avg_delay = max(float(m["delay_days"].fillna(0).mean()), float(p["delay_days"].fillna(0).mean()) if len(p) else 0)
        blocked = int(m["status"].eq("Blocked").sum()) if len(m) else 0
        open_critical = int(((r["severity"] == "Critical") & (~r["status"].isin(["Closed", "Resolved"]))).sum()) if len(r) else 0
        open_high = int(((r["severity"] == "High") & (~r["status"].isin(["Closed", "Resolved"]))).sum()) if len(r) else 0
        overdue_actions = int(((a["status"] != "Completed") & (pd.to_datetime(a["due_date"]) < reference)).sum()) if len(a) else 0
        closure_rate = (a["status"] == "Completed").mean() if len(a) else 0
        supplier_reliability = p["reliability_score_base"].mean() if len(p) else 85
        launch_days = int((pd.to_datetime(collection["launch_date"]) - reference).days)
        unresolved_issue_count = blocked + open_critical + open_high + overdue_actions

        score = 100.0
        score -= open_critical * 8
        score -= open_high * 3
        score -= blocked * 5
        score -= overdue_actions * 4
        score -= min(avg_delay * 1.8, 22)
        score -= max(0, 82 - supplier_reliability) * 0.45
        if launch_days <= 45 and unresolved_issue_count:
            score -= min(18, (46 - max(launch_days, 0)) / 3 + unresolved_issue_count)
        score += completed_rate * 8
        score += closure_rate * 5
        score = float(np.clip(score, 0, 100))

        rows.append(
            {
                "collection_id": collection_id,
                "readiness_score": round(score, 1),
                "readiness_band": readiness_band_from_score(score),
                "launch_countdown_days": launch_days,
                "completed_milestone_rate": round(completed_rate, 3),
                "open_critical_risks": open_critical,
                "blocked_milestones": blocked,
                "overdue_actions": overdue_actions,
                "average_delay_days": round(avg_delay, 1),
                "supplier_reliability_score": round(float(supplier_reliability), 1),
            }
        )
    return pd.DataFrame(rows)


def readiness_band_from_score(score: float) -> str:
    if score >= 85:
        return "Ready"
    if score >= 70:
        return "Watch"
    if score >= 50:
        return "At Risk"
    return "Critical"
