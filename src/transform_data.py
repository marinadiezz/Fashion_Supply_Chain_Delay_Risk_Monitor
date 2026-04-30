from __future__ import annotations

import pandas as pd

from calculate_kpis import supplier_scorecard
from risk_scoring import add_risk_scoring, calculate_readiness_scores
from utils import PROCESSED_DIR, RAW_DIR, ensure_dirs, load_all, parse_dates


REFERENCE_DATE = pd.Timestamp("2026-04-25")


def load_raw_tables() -> dict[str, pd.DataFrame]:
    tables = {}
    for path in RAW_DIR.glob("*.csv"):
        tables[path.stem] = pd.read_csv(path)
    date_map = {
        "collections": ["launch_date"],
        "purchase_orders": ["planned_order_date", "actual_order_date", "planned_ship_date", "actual_ship_date", "planned_arrival_date", "actual_arrival_date"],
        "milestones": ["planned_date", "actual_date"],
        "risks": ["date_identified", "target_resolution_date"],
        "incidents": ["date_opened", "date_closed"],
        "actions": ["due_date", "completion_date"],
    }
    for name, columns in date_map.items():
        if name in tables:
            tables[name] = parse_dates(tables[name], columns)
    return tables


def enrich_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    brands = tables["brands"].copy()
    collections = tables["collections"].merge(brands[["brand_id", "brand_name", "target_segment", "price_tier"]], on="brand_id", how="left")
    suppliers = tables["suppliers"].copy()

    supplier_lookup_cols = [
        "supplier_id",
        "supplier_name",
        "country",
        "supplier_city",
        "supplier_lat",
        "supplier_lon",
        "region",
        "supplier_specialty",
        "reliability_score_base",
        "capacity_band",
        "escalation_level",
    ]
    supplier_lookup_cols = [c for c in supplier_lookup_cols if c in suppliers.columns]

    purchase_orders = tables["purchase_orders"].merge(
        collections[["collection_id", "collection_name", "brand_id", "brand_name", "market", "season", "launch_date", "launch_channel"]],
        on="collection_id",
        how="left",
    ).merge(
        suppliers[supplier_lookup_cols],
        on="supplier_id",
        how="left",
    )
    purchase_orders["delay_days"] = (
        (purchase_orders["actual_arrival_date"].fillna(REFERENCE_DATE) - purchase_orders["planned_arrival_date"]).dt.days.clip(lower=0)
    )
    purchase_orders["lead_time_actual_days"] = (
        purchase_orders["actual_ship_date"].fillna(REFERENCE_DATE) - purchase_orders["actual_order_date"]
    ).dt.days.clip(lower=1)
    purchase_orders["planned_lead_time_days"] = (purchase_orders["planned_ship_date"] - purchase_orders["planned_order_date"]).dt.days
    purchase_orders["lead_time_variance_days"] = purchase_orders["lead_time_actual_days"] - purchase_orders["planned_lead_time_days"]

    milestones = tables["milestones"].merge(
        collections[["collection_id", "collection_name", "brand_id", "brand_name", "market", "season", "launch_date", "launch_channel"]],
        on="collection_id",
        how="left",
    )
    milestones["days_to_launch_at_plan"] = (milestones["launch_date"] - milestones["planned_date"]).dt.days
    milestones["is_overdue"] = (milestones["status"].ne("Completed")) & (milestones["planned_date"] < REFERENCE_DATE)

    risks = add_risk_scoring(
        tables["risks"].merge(
            collections[["collection_id", "collection_name", "brand_id", "brand_name", "market", "season", "launch_date", "launch_channel"]],
            on="collection_id",
            how="left",
        )
    )
    risks["is_open"] = ~risks["status"].isin(["Closed", "Resolved"])

    incidents = tables["incidents"].merge(
        collections[["collection_id", "collection_name", "brand_id", "brand_name", "market", "season", "launch_date"]],
        on="collection_id",
        how="left",
    ).merge(
        suppliers[[c for c in ["supplier_id", "supplier_name", "country", "supplier_city", "region", "reliability_score_base"] if c in suppliers.columns]],
        on="supplier_id",
        how="left",
    )

    actions = tables["actions"].merge(
        risks[["risk_id", "risk_type", "severity", "risk_score", "workstream"]],
        left_on="linked_risk_id",
        right_on="risk_id",
        how="left",
    ).merge(
        collections[["collection_id", "collection_name", "brand_id", "brand_name", "market", "season", "launch_date", "launch_channel"]],
        on="collection_id",
        how="left",
    )
    actions["is_overdue"] = (actions["status"] != "Completed") & (actions["due_date"] < REFERENCE_DATE)
    actions["due_in_14_days"] = (actions["status"] != "Completed") & (actions["due_date"].between(REFERENCE_DATE, REFERENCE_DATE + pd.Timedelta(days=14)))

    readiness = calculate_readiness_scores(collections, milestones, risks, actions, purchase_orders, suppliers, REFERENCE_DATE)
    collections = collections.merge(readiness, on="collection_id", how="left")
    suppliers = suppliers.merge(
        supplier_scorecard(purchase_orders, suppliers, incidents, risks)[
            [
                "supplier_id",
                "avg_delay",
                "lead_time_variance",
                "incidents",
                "open_incidents",
                "main_incident_type",
                "open_linked_risks",
                "open_critical_risks",
                "supplier_risk_score",
                "supplier_risk_band",
                "suggested_pm_action",
                "linked_collections",
                "main_sku_family",
            ]
        ],
        on="supplier_id",
        how="left",
    )

    return {
        "brands": brands,
        "collections": collections,
        "suppliers": suppliers,
        "purchase_orders": purchase_orders,
        "milestones": milestones,
        "risks": risks,
        "incidents": incidents,
        "actions": actions,
    }


def save_processed(tables: dict[str, pd.DataFrame]) -> None:
    ensure_dirs()
    for name, df in tables.items():
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)


def main() -> None:
    raw = load_raw_tables()
    required = {"brands", "collections", "suppliers", "purchase_orders", "milestones", "risks", "incidents", "actions"}
    missing = required - set(raw)
    if missing:
        raise FileNotFoundError(f"Missing raw tables: {sorted(missing)}. Run python src/generate_data.py first.")
    processed = enrich_tables(raw)
    save_processed(processed)
    print("Processed fashion supply chain data saved in data/processed")


if __name__ == "__main__":
    main()
