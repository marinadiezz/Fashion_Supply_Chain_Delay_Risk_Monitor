from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from risk_scoring import calculate_risk_score, classify_severity
from utils import RAW_DIR, ensure_dirs


SEED = 42
REFERENCE_DATE = pd.Timestamp("2026-04-25")
rng = np.random.default_rng(SEED)


SOURCE_NOTE = "Inditex Annual Report 2024 and official brand websites; operational rows are scenario records derived from public portfolio facts."

BRANDS = [
    ("BR001", "Zara", "women, men and kids", "trend-led fashion with broad category reach", "apparel", "mid", "integrated stores and online", 3140105, "Zara and Zara Home selling space reported together by Inditex in 2024"),
    ("BR002", "Pull&Bear", "young casual fashion", "casual, urban and youth culture-led fashion", "young fashion", "accessible", "integrated stores and online", 396522, "2024 Inditex selling space by concept"),
    ("BR003", "Massimo Dutti", "premium contemporary", "elevated tailoring, knitwear and refined wardrobe essentials", "premium apparel", "premium", "integrated stores and online", 219611, "2024 Inditex selling space by concept"),
    ("BR004", "Bershka", "young trend", "music, social and street trend-led fashion", "young fashion", "accessible", "integrated stores and online", 481556, "2024 Inditex selling space by concept"),
    ("BR005", "Stradivarius", "young womenswear", "feminine, accessible and trend-led collections", "womenswear", "accessible", "integrated stores and online", 319720, "2024 Inditex selling space by concept"),
    ("BR006", "Oysho", "activewear and lingerie", "sport, athleisure, lingerie and comfort-led essentials", "activewear", "mid", "integrated stores and online", 93061, "2024 Inditex selling space by concept"),
    ("BR007", "Zara Home", "home and lifestyle", "home textiles, furniture and lifestyle objects", "home", "mid", "integrated stores and online", 0, "Included with Zara in 2024 Inditex concept reporting"),
]

SEASONS = ["SS25", "Summer 25", "AW25", "Holiday 25"]
MARKETS = ["Spain", "Portugal", "France", "Germany", "Italy", "United Kingdom", "Netherlands", "Poland", "Mexico", "United States"]
CHANNELS = ["Retail", "E-commerce", "Omnichannel", "Marketplace"]
SKU_FAMILIES = ["dresses", "tailoring", "denim", "knitwear", "outerwear", "footwear", "accessories", "kids basics", "home textiles", "activewear", "formalwear", "bags"]
SUPPLIER_COUNTRIES = {
    "Spain": "Western Europe",
    "Portugal": "Western Europe",
    "Turkey": "Nearshore EMEA",
    "Morocco": "Nearshore EMEA",
    "Bangladesh": "South Asia",
    "Vietnam": "Southeast Asia",
    "China": "East Asia",
    "India": "South Asia",
    "Italy": "Western Europe",
}
SUPPLIER_CITY_COORDS = {
    "Spain": [("Barcelona", 41.3874, 2.1686), ("Valencia", 39.4699, -0.3763)],
    "Portugal": [("Porto", 41.1579, -8.6291), ("Braga", 41.5454, -8.4265)],
    "Turkey": [("Istanbul", 41.0082, 28.9784), ("Izmir", 38.4237, 27.1428)],
    "Morocco": [("Tangier", 35.7595, -5.8340), ("Casablanca", 33.5731, -7.5898)],
    "Bangladesh": [("Dhaka", 23.8103, 90.4125)],
    "Vietnam": [("Ho Chi Minh City", 10.8231, 106.6297)],
    "China": [("Guangzhou", 23.1291, 113.2644)],
    "India": [("Tiruppur", 11.1085, 77.3411)],
    "Italy": [("Milan", 45.4642, 9.1900)],
}
MARKET_HUBS = {
    "Spain": "Arteixo / Zaragoza logistics platform",
    "Portugal": "Porto DC",
    "France": "Paris North Hub",
    "Germany": "Hamburg DC",
    "Italy": "Milan DC",
    "United Kingdom": "London Gateway",
    "Netherlands": "Lelystad logistics platform",
    "Poland": "Poznan DC",
    "Mexico": "Mexico City Hub",
    "United States": "New Jersey DC",
}
TRANSPORT_BY_REGION = {
    "Western Europe": ["Road", "Intermodal"],
    "Nearshore EMEA": ["Road", "Short-sea", "Air"],
    "South Asia": ["Ocean", "Air"],
    "Southeast Asia": ["Ocean", "Air"],
    "East Asia": ["Ocean", "Air"],
}
SPECIALTIES = ["woven apparel", "denim", "knitwear", "outerwear", "leather goods", "footwear", "kidswear", "home textiles", "formal tailoring", "jersey basics", "activewear"]
WORKSTREAMS = ["design", "sourcing", "production", "quality_control", "inbound_logistics", "warehouse_allocation", "ecommerce", "marketing", "retail_readiness", "launch_governance"]
MILESTONE_SEQUENCE = [
    ("design", "Final design sign-off", 155),
    ("design", "Fabric approval", 145),
    ("sourcing", "Supplier nomination", 135),
    ("sourcing", "Purchase order confirmed", 122),
    ("production", "Size set sample approved", 105),
    ("production", "Production start", 92),
    ("quality_control", "Mid-production inspection", 68),
    ("quality_control", "Final quality inspection", 46),
    ("inbound_logistics", "Shipment booking confirmed", 38),
    ("inbound_logistics", "Customs documentation completed", 29),
    ("warehouse_allocation", "Warehouse slot confirmed", 21),
    ("ecommerce", "Product copy uploaded", 18),
    ("ecommerce", "Product images approved", 15),
    ("ecommerce", "Pricing approved", 13),
    ("marketing", "Campaign assets delivered", 12),
    ("retail_readiness", "Retail briefing completed", 9),
    ("launch_governance", "Launch readiness review", 5),
    ("launch_governance", "Go-live approval", 2),
]
OWNERS = ["PMO", "Sourcing Lead", "Production Planner", "Quality Manager", "Logistics Lead", "E-commerce Producer", "Marketing Manager", "Retail Operations", "Merchandising", "Compliance Lead"]
RISK_TYPES = {
    "supplier capacity": "Supplier capacity issue may compress production window",
    "quality failure": "Inspection failure could require rework before shipment",
    "logistics delay": "Transport disruption may delay inbound arrival",
    "customs issue": "Customs hold risk linked to incomplete documents",
    "ecommerce readiness": "Missing product content may block digital go-live",
    "marketing delay": "Campaign assets may miss launch handover",
    "stock allocation": "Allocation dispute may reduce launch coverage",
    "compliance issue": "Labeling or sustainability document may need review",
    "packaging delay": "Packaging approval may miss production handoff",
    "production backlog": "Factory backlog may push final inspection",
    "data/content issue": "Product data may need manual cleanup before publishing",
}
INCIDENT_TYPES = ["Fabric approval delayed", "Supplier capacity issue", "Factory production backlog", "Quality inspection failed", "Rework required", "Customs hold", "Transport strike", "Port congestion", "Warehouse slot unavailable", "Packaging approval delayed", "E-commerce product images missing", "Product descriptions not localized", "Pricing not approved", "Size curve mismatch", "Stock allocation dispute", "Marketing campaign assets delayed", "Retail staff training incomplete", "Sustainability certificate missing", "Labeling compliance issue", "Barcode mismatch", "Late sample approval", "Supplier documentation incomplete"]
IMPACTS = ["Launch scope reduced", "Partial shipment required", "Extra freight cost", "E-commerce launch delayed", "Store allocation changed", "Campaign timing affected", "Manual rework required"]
ACTION_TYPES = ["Expedite shipment", "Switch supplier", "Approve partial launch", "Escalate quality review", "Add warehouse slot", "Update product content", "Reprioritize campaign assets", "Validate compliance documents", "Reallocate stock", "Confirm contingency plan"]


def choice(values, p=None):
    return rng.choice(values, p=p)


def date_str(date: pd.Timestamp | None) -> str | None:
    return None if pd.isna(date) or date is None else pd.Timestamp(date).date().isoformat()


def build_brands() -> pd.DataFrame:
    return pd.DataFrame(
        BRANDS,
        columns=[
            "brand_id",
            "brand_name",
            "target_segment",
            "positioning",
            "main_category",
            "price_tier",
            "channel_focus",
            "reported_selling_space_m2_2024",
            "source_note",
        ],
    )


def build_collections(brands: pd.DataFrame, n: int = 30) -> pd.DataFrame:
    names_by_brand = {
        "Zara": ["Woman Studio", "Man Essentials", "Kids Back to School", "Origins", "Evening"],
        "Pull&Bear": ["Campus", "Denim Drop", "Graphic Edit", "Festival"],
        "Massimo Dutti": ["Limited Edition", "Tailoring", "Knitwear", "Atelier"],
        "Bershka": ["B Series", "Denim Core", "Partywear", "Street"],
        "Stradivarius": ["Summer Stories", "Denim", "Occasionwear", "Accessories"],
        "Oysho": ["Training", "Ski", "Compressive", "Lounge"],
        "Zara Home": ["Bed Linen", "Tableware", "Kids Home", "Bathroom"],
    }
    rows = []
    for i in range(1, n + 1):
        brand = brands.sample(1, random_state=SEED + i).iloc[0]
        launch_date = REFERENCE_DATE + pd.Timedelta(days=int(rng.integers(65, 340)))
        collection_names = names_by_brand.get(brand["brand_name"], ["Core", "Market Drop"])
        season = choice(SEASONS)
        rows.append(
            {
                "collection_id": f"COL{i:03d}",
                "brand_id": brand["brand_id"],
                "collection_name": f"{brand['brand_name']} {choice(collection_names)} {season}",
                "season": season,
                "market": choice(MARKETS),
                "launch_date": date_str(launch_date),
                "launch_channel": choice(CHANNELS, p=[0.25, 0.28, 0.37, 0.10]),
                "category_mix": ", ".join(rng.choice(SKU_FAMILIES, size=int(rng.integers(2, 5)), replace=False)),
                "strategic_priority": choice(["Core", "Growth", "Hero Launch", "Market Test"], p=[0.36, 0.30, 0.22, 0.12]),
                "launch_criticality": choice(["Standard", "High", "Board Review"], p=[0.48, 0.36, 0.16]),
                "commercial_priority": choice(["Low", "Medium", "High", "Strategic"], p=[0.12, 0.42, 0.31, 0.15]),
                "revenue_exposure_band": choice(["Low", "Medium", "High", "Strategic"], p=[0.16, 0.39, 0.32, 0.13]),
                "planned_scope_skus": int(rng.integers(65, 460)),
                "data_source": SOURCE_NOTE,
            }
        )
    return pd.DataFrame(rows)


def build_suppliers(n: int = 34) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        country = choice(list(SUPPLIER_COUNTRIES))
        city, lat, lon = SUPPLIER_CITY_COORDS[country][int(rng.integers(0, len(SUPPLIER_CITY_COORDS[country])))]
        reliability = int(np.clip(rng.normal(82, 10), 55, 98))
        risk = round(float(np.clip((100 - reliability) / 55 + rng.normal(0.04, 0.05), 0.05, 0.85)), 2)
        rows.append(
            {
                "supplier_id": f"SUP{i:03d}",
                "supplier_name": f"Inditex {country} Cluster Partner {i:02d}",
                "country": country,
                "supplier_city": city,
                "supplier_lat": round(float(lat + rng.normal(0, 0.08)), 4),
                "supplier_lon": round(float(lon + rng.normal(0, 0.08)), 4),
                "region": SUPPLIER_COUNTRIES[country],
                "supplier_specialty": choice(SPECIALTIES),
                "lead_time_planned_days": int(rng.integers(28, 88)),
                "reliability_score_base": reliability,
                "capacity_band": choice(["Low", "Medium", "High", "Strategic"], p=[0.14, 0.42, 0.30, 0.14]),
                "sustainability_rating": choice(["A", "B", "C", "D"], p=[0.24, 0.43, 0.25, 0.08]),
                "historical_delay_risk": risk,
                "escalation_level": choice(["Business as usual", "PMO watch", "Sourcing review", "Executive escalation"], p=[0.38, 0.31, 0.22, 0.09]),
                "data_source": SOURCE_NOTE,
            }
        )
    return pd.DataFrame(rows)


def build_purchase_orders(collections: pd.DataFrame, suppliers: pd.DataFrame, n: int = 390) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        col = collections.sample(1, random_state=SEED + i * 3).iloc[0]
        sup = suppliers.sample(1, random_state=SEED + i * 7).iloc[0]
        launch = pd.to_datetime(col["launch_date"])
        transport_mode = choice(TRANSPORT_BY_REGION[sup["region"]])
        mode_risk = {"Road": 0.14, "Intermodal": 0.18, "Short-sea": 0.24, "Ocean": 0.34, "Air": 0.10}[transport_mode]
        planned_order = launch - pd.Timedelta(days=int(rng.integers(95, 155)))
        actual_order_delay = max(0, int(rng.normal(1.5 + sup["historical_delay_risk"] * 5, 3)))
        actual_order = planned_order + pd.Timedelta(days=actual_order_delay)
        planned_ship = planned_order + pd.Timedelta(days=int(sup["lead_time_planned_days"]))
        delay_mean = (100 - sup["reliability_score_base"]) / 6
        ship_delay = int(np.clip(rng.normal(delay_mean, 7), -4, 38))
        actual_ship = planned_ship + pd.Timedelta(days=ship_delay)
        transit = int(rng.integers(5, 25))
        planned_arrival = planned_ship + pd.Timedelta(days=transit)
        arrival_noise = int(np.clip(ship_delay + rng.normal(1 + mode_risk * 5, 4), -3, 45))
        actual_arrival = planned_arrival + pd.Timedelta(days=arrival_noise)
        if actual_arrival > launch - pd.Timedelta(days=3):
            status = choice(["Delayed", "Partial", "At Risk"], p=[0.55, 0.20, 0.25])
        elif arrival_noise > 2:
            status = choice(["Delayed", "Received", "In Transit"], p=[0.45, 0.35, 0.20])
        else:
            status = choice(["Received", "In Transit", "Confirmed"], p=[0.55, 0.30, 0.15])
        if status in ["Confirmed", "In Transit"] and rng.random() < 0.32:
            actual_arrival_out = None
        else:
            actual_arrival_out = actual_arrival
        lead_actual = (actual_ship - actual_order).days
        rows.append(
            {
                "po_id": f"PO{i:04d}",
                "collection_id": col["collection_id"],
                "supplier_id": sup["supplier_id"],
                "sku_family": choice(SKU_FAMILIES),
                "quantity": int(rng.integers(800, 26000)),
                "planned_order_date": date_str(planned_order),
                "actual_order_date": date_str(actual_order),
                "planned_ship_date": date_str(planned_ship),
                "actual_ship_date": date_str(actual_ship if status != "Confirmed" else None),
                "planned_arrival_date": date_str(planned_arrival),
                "actual_arrival_date": date_str(actual_arrival_out),
                "status": status,
                "delay_days": max(0, arrival_noise),
                "lead_time_actual_days": max(1, lead_actual),
                "lead_time_variance_days": lead_actual - int(sup["lead_time_planned_days"]),
                "transport_mode": transport_mode,
                "destination_hub": MARKET_HUBS[col["market"]],
                "destination_market": col["market"],
                "route_risk_score": round(float(np.clip(sup["historical_delay_risk"] * 60 + mode_risk * 55 + max(0, arrival_noise), 0, 100)), 1),
                "avg_route_delay_days": max(0, arrival_noise),
            }
        )
    return pd.DataFrame(rows)


def build_milestones(collections: pd.DataFrame) -> pd.DataFrame:
    rows = []
    idx = 1
    for _, col in collections.iterrows():
        launch = pd.to_datetime(col["launch_date"])
        previous_id = None
        cascade_pressure = 0.0
        for workstream, name, offset in MILESTONE_SEQUENCE:
            planned = launch - pd.Timedelta(days=offset + int(rng.integers(-4, 5)))
            base_p = 0.16 + cascade_pressure
            blocked_p = 0.04 + cascade_pressure / 2
            roll = rng.random()
            if planned > REFERENCE_DATE:
                status = choice(["Not Started", "In Progress", "At Risk", "Blocked"], p=[0.35, 0.34, 0.23, 0.08])
            elif roll < blocked_p:
                status = "Blocked"
            elif roll < base_p:
                status = "Delayed"
            elif roll < base_p + 0.20:
                status = "At Risk"
            else:
                status = "Completed"
            delay = 0
            actual = None
            if status == "Completed":
                delay = int(np.clip(rng.normal(cascade_pressure * 8, 5), -5, 24))
                actual = planned + pd.Timedelta(days=delay)
            elif status in ["Delayed", "Blocked", "At Risk"]:
                delay = int(np.clip(rng.normal(4 + cascade_pressure * 12, 5), 1, 32))
            if status in ["Delayed", "Blocked"]:
                cascade_pressure = min(0.35, cascade_pressure + 0.05 + delay / 160)
            else:
                cascade_pressure = max(0, cascade_pressure - 0.015)
            blocker = ""
            if status == "Blocked":
                blocker = choice(["Dependency not complete", "Supplier documentation incomplete", "Quality rework pending", "Content approval missing", "Warehouse slot not available", "Pricing decision pending"])
            rows.append(
                {
                    "milestone_id": f"MS{idx:05d}",
                    "collection_id": col["collection_id"],
                    "workstream": workstream,
                    "milestone_name": name,
                    "planned_date": date_str(planned),
                    "actual_date": date_str(actual),
                    "owner": choice(OWNERS),
                    "status": status,
                    "dependency_id": previous_id,
                    "delay_days": max(0, delay),
                    "is_blocked": status == "Blocked",
                    "blocker_reason": blocker,
                }
            )
            previous_id = f"MS{idx:05d}"
            idx += 1
    return pd.DataFrame(rows)


def build_risks(collections: pd.DataFrame, milestones: pd.DataFrame, n: int = 190) -> pd.DataFrame:
    rows = []
    pressure = milestones.groupby("collection_id")["delay_days"].mean().to_dict()
    for i in range(1, n + 1):
        col = collections.sample(1, random_state=SEED + i * 11).iloc[0]
        rtype = choice(list(RISK_TYPES))
        prob = int(np.clip(rng.integers(1, 5) + pressure.get(col["collection_id"], 0) / 9, 1, 5))
        impact = int(choice([2, 3, 4, 5], p=[0.18, 0.32, 0.31, 0.19]))
        score = calculate_risk_score(prob, impact)
        severity = classify_severity(score)
        identified = pd.to_datetime(col["launch_date"]) - pd.Timedelta(days=int(rng.integers(18, 120)))
        rows.append(
            {
                "risk_id": f"RSK{i:04d}",
                "collection_id": col["collection_id"],
                "workstream": choice(WORKSTREAMS),
                "risk_type": rtype,
                "risk_description": RISK_TYPES[rtype],
                "probability": prob,
                "impact": impact,
                "severity": severity,
                "risk_score": score,
                "owner": choice(OWNERS),
                "status": choice(["Open", "Monitoring", "Escalated", "Mitigating", "Closed"], p=[0.25, 0.22, 0.15, 0.24, 0.14]),
                "mitigation_status": choice(["Not Started", "In Progress", "Completed", "Overdue"], p=[0.18, 0.44, 0.24, 0.14]),
                "date_identified": date_str(identified),
                "target_resolution_date": date_str(identified + pd.Timedelta(days=int(rng.integers(10, 45)))),
            }
        )
    return pd.DataFrame(rows)


def build_incidents(collections: pd.DataFrame, suppliers: pd.DataFrame, purchase_orders: pd.DataFrame, n: int = 165) -> pd.DataFrame:
    rows = []
    po_pool = purchase_orders.merge(suppliers[["supplier_id", "historical_delay_risk"]], on="supplier_id")
    weights = po_pool["historical_delay_risk"] + po_pool["delay_days"].clip(0, 20) / 35 + 0.05
    selected = po_pool.sample(n=n, replace=True, weights=weights, random_state=SEED)
    for i, (_, po) in enumerate(selected.iterrows(), start=1):
        opened = pd.to_datetime(po["planned_ship_date"]) + pd.Timedelta(days=int(rng.integers(-12, 20)))
        delay = int(np.clip(rng.normal(po["delay_days"] + 3, 5), 1, 36))
        status = choice(["Open", "In Review", "Resolved", "Closed"], p=[0.24, 0.22, 0.30, 0.24])
        closed = None if status in ["Open", "In Review"] else opened + pd.Timedelta(days=int(rng.integers(3, 24)))
        rows.append(
            {
                "incident_id": f"INC{i:04d}",
                "supplier_id": po["supplier_id"],
                "collection_id": po["collection_id"],
                "related_po_id": po["po_id"],
                "issue_type": choice(INCIDENT_TYPES),
                "root_cause": choice(["Capacity planning", "Documentation gap", "Inspection failure", "Transport disruption", "Late approval", "System data mismatch", "Material shortage"]),
                "date_opened": date_str(opened),
                "date_closed": date_str(closed),
                "delay_days": delay,
                "business_impact": choice(IMPACTS),
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def build_actions(risks: pd.DataFrame, n: int = 240) -> pd.DataFrame:
    rows = []
    selected = risks.sample(n=n, replace=True, random_state=SEED)
    for i, (_, risk) in enumerate(selected.iterrows(), start=1):
        due = pd.to_datetime(risk["target_resolution_date"]) + pd.Timedelta(days=int(rng.integers(-10, 16)))
        status = choice(["Not Started", "In Progress", "Completed", "Overdue"], p=[0.18, 0.39, 0.29, 0.14])
        completion = None
        if status == "Completed":
            completion = due + pd.Timedelta(days=int(rng.integers(-8, 5)))
        rows.append(
            {
                "action_id": f"ACT{i:04d}",
                "linked_risk_id": risk["risk_id"],
                "collection_id": risk["collection_id"],
                "action_type": choice(ACTION_TYPES),
                "action_description": f"{choice(ACTION_TYPES)} for {risk['risk_type']} risk before launch gate",
                "owner": risk["owner"],
                "due_date": date_str(due),
                "completion_date": date_str(completion),
                "status": status,
                "expected_impact": choice(["Reduce launch delay", "Protect launch scope", "Lower rework risk", "Improve readiness confidence", "Contain cost exposure"]),
                "priority": choice(["Low", "Medium", "High", "Critical"], p=[0.12, 0.38, 0.33, 0.17]),
            }
        )
    return pd.DataFrame(rows)


def save_tables(tables: dict[str, pd.DataFrame], output_dir: Path = RAW_DIR) -> None:
    ensure_dirs()
    for name, df in tables.items():
        df.to_csv(output_dir / f"{name}.csv", index=False)


def main() -> None:
    brands = build_brands()
    collections = build_collections(brands)
    suppliers = build_suppliers()
    purchase_orders = build_purchase_orders(collections, suppliers)
    milestones = build_milestones(collections)
    risks = build_risks(collections, milestones)
    incidents = build_incidents(collections, suppliers, purchase_orders)
    actions = build_actions(risks)
    save_tables(
        {
            "brands": brands,
            "collections": collections,
            "suppliers": suppliers,
            "purchase_orders": purchase_orders,
            "milestones": milestones,
            "risks": risks,
            "incidents": incidents,
            "actions": actions,
        }
    )
    print("Raw Inditex-context fashion supply chain scenario data generated in data/raw")


if __name__ == "__main__":
    main()
