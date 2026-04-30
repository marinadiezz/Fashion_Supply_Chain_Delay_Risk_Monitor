from __future__ import annotations

import csv
import html
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
DOCS = ROOT / "docs"
SCREENSHOTS = ROOT / "assets" / "screenshots"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / f"{name}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def num(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def bar_rows(items: list[tuple[str, float]], suffix: str = "", max_value: float | None = None) -> str:
    if not items:
        return ""
    cap = max_value or max(value for _, value in items) or 1
    rows = []
    for label, value in items:
        width = max(4, min(100, value / cap * 100))
        rows.append(
            f"""
            <div class="bar-row">
              <span>{html.escape(label)}</span>
              <div class="bar-track"><div class="bar-fill" style="width:{width:.1f}%"></div></div>
              <strong>{value:.1f}{suffix}</strong>
            </div>
            """
        )
    return "\n".join(rows)


def screenshot_svg(title: str, subtitle: str, stats: list[tuple[str, str]], filename: str) -> None:
    stat_blocks = []
    x = 44
    for label, value in stats:
        stat_blocks.append(
            f"""
            <rect x="{x}" y="150" width="210" height="112" rx="8" fill="#ffffff" stroke="#d8dee8"/>
            <text x="{x + 18}" y="190" font-size="14" fill="#5b6472">{html.escape(label)}</text>
            <text x="{x + 18}" y="232" font-size="30" font-weight="700" fill="#172033">{html.escape(value)}</text>
            """
        )
        x += 232
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="680" viewBox="0 0 1200 680">
  <rect width="1200" height="680" fill="#f5f7fb"/>
  <rect x="28" y="28" width="1144" height="624" rx="14" fill="#ffffff" stroke="#d7deea"/>
  <text x="56" y="86" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="34" font-weight="700" fill="#172033">{html.escape(title)}</text>
  <text x="56" y="124" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="17" fill="#5b6472">{html.escape(subtitle)}</text>
  {''.join(stat_blocks)}
  <rect x="56" y="318" width="1088" height="24" rx="12" fill="#e8edf5"/>
  <rect x="56" y="318" width="782" height="24" rx="12" fill="#2f6f73"/>
  <rect x="56" y="378" width="506" height="42" rx="7" fill="#eaf4f1"/>
  <rect x="584" y="378" width="386" height="42" rx="7" fill="#fff3df"/>
  <rect x="56" y="454" width="634" height="42" rx="7" fill="#eef1f7"/>
  <rect x="712" y="454" width="286" height="42" rx="7" fill="#f8e7e7"/>
  <text x="56" y="580" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="16" fill="#5b6472">Static recruiter preview generated from synthetic scenario data. Full interactive app runs with Streamlit.</text>
</svg>
"""
    (SCREENSHOTS / filename).write_text(svg, encoding="utf-8")


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)

    collections = read_csv("collections")
    purchase_orders = read_csv("purchase_orders")
    milestones = read_csv("milestones")
    risks = read_csv("risks")
    actions = read_csv("actions")
    suppliers = read_csv("suppliers")

    collection_count = len(collections)
    supplier_count = len(suppliers)
    order_count = len(purchase_orders)
    avg_readiness = sum(num(row["readiness_score"]) for row in collections) / max(collection_count, 1)
    at_risk = sum(row["readiness_band"] in {"At Risk", "Critical"} for row in collections)
    blocked = sum(row["status"] == "Blocked" for row in milestones)
    open_critical = sum(row["severity"] == "Critical" and row["status"] not in {"Closed", "Resolved"} for row in risks)
    overdue = sum(row["status"] != "Completed" for row in actions if row.get("due_date", "") < "2026-04-25")
    delayed_pos = [num(row["delay_days"]) for row in purchase_orders if num(row["delay_days"]) > 0]
    avg_po_delay = sum(delayed_pos) / max(len(delayed_pos), 1)

    band_counts = Counter(row["readiness_band"] for row in collections)
    band_items = [(band, float(band_counts.get(band, 0))) for band in ["Ready", "Watch", "At Risk", "Critical"]]

    workstream_delay: dict[str, float] = defaultdict(float)
    for row in milestones:
        workstream_delay[row["workstream"]] += max(0, num(row["delay_days"]))
    workstream_items = sorted(workstream_delay.items(), key=lambda item: item[1], reverse=True)[:6]

    supplier_delay: dict[str, list[float]] = defaultdict(list)
    for row in purchase_orders:
        supplier_delay[row["supplier_name"]].append(max(0, num(row["delay_days"])))
    supplier_items = sorted(
        ((name, sum(values) / max(len(values), 1)) for name, values in supplier_delay.items()),
        key=lambda item: item[1],
        reverse=True,
    )[:6]

    top_collections = sorted(collections, key=lambda row: num(row["readiness_score"]))[:6]
    top_rows = "\n".join(
        f"<tr><td>{html.escape(row['collection_name'])}</td><td>{html.escape(row['brand_name'])}</td><td>{html.escape(row['market'])}</td><td>{num(row['readiness_score']):.1f}</td><td>{html.escape(row['readiness_band'])}</td></tr>"
        for row in top_collections
    )

    screenshot_svg(
        "Executive Overview",
        "Portfolio readiness, blocked work, and open critical risks",
        [
            ("Avg readiness", f"{avg_readiness:.1f}"),
            ("At-risk launches", str(at_risk)),
            ("Blocked milestones", str(blocked)),
            ("Open critical risks", str(open_critical)),
        ],
        "executive_overview.svg",
    )
    screenshot_svg(
        "Supplier Watchlist",
        "Lead-time variance and incident exposure by sourcing partner",
        [
            ("Suppliers", str(supplier_count)),
            ("Purchase orders", str(order_count)),
            ("Avg positive PO delay", f"{avg_po_delay:.1f}d"),
            ("Overdue actions", str(overdue)),
        ],
        "supplier_watchlist.svg",
    )
    screenshot_svg(
        "Risk Monitoring",
        "Scenario risks linked to collections, workstreams, and mitigation owners",
        [
            ("Scenario records", str(len(risks))),
            ("Open critical", str(open_critical)),
            ("Blocked milestones", str(blocked)),
            ("At-risk share", pct(at_risk / max(collection_count, 1))),
        ],
        "risk_monitoring.svg",
    )

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fashion Supply Chain Delay & Risk Monitor</title>
  <style>
    :root {{ --ink:#172033; --muted:#5b6472; --line:#d8dee8; --bg:#f5f7fb; --teal:#2f6f73; --amber:#b56b2a; --red:#b94747; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter, Segoe UI, Arial, sans-serif; color:var(--ink); background:var(--bg); }}
    header {{ padding:44px 6vw 26px; background:#fff; border-bottom:1px solid var(--line); }}
    main {{ padding:28px 6vw 52px; }}
    h1 {{ margin:0 0 10px; font-size:clamp(30px, 5vw, 54px); letter-spacing:0; }}
    h2 {{ margin:34px 0 14px; font-size:24px; }}
    p {{ max-width:980px; line-height:1.6; color:var(--muted); }}
    .kpis {{ display:grid; grid-template-columns:repeat(4, minmax(160px, 1fr)); gap:14px; margin-top:24px; }}
    .card {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:18px; }}
    .metric-label {{ color:var(--muted); font-size:13px; }}
    .metric-value {{ font-size:32px; font-weight:750; margin-top:8px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    .bar-row {{ display:grid; grid-template-columns:150px 1fr 70px; gap:12px; align-items:center; margin:12px 0; font-size:14px; }}
    .bar-track {{ height:12px; background:#e8edf5; border-radius:99px; overflow:hidden; }}
    .bar-fill {{ height:100%; background:var(--teal); }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    th, td {{ padding:12px 14px; border-bottom:1px solid var(--line); text-align:left; font-size:14px; }}
    th {{ background:#eef1f7; }}
    .note {{ font-size:14px; color:var(--muted); }}
    .links a {{ color:var(--teal); font-weight:700; margin-right:18px; }}
    @media (max-width: 900px) {{ .kpis, .grid {{ grid-template-columns:1fr; }} .bar-row {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Fashion Supply Chain Delay & Risk Monitor</h1>
    <p>A portfolio-ready analytics project that models launch readiness, supplier performance, operational blockers, and mitigation ownership for a multi-brand fashion supply chain.</p>
    <p class="links"><a href="#business-view">Business view</a><a href="#lowest-readiness">Lowest readiness</a><a href="#portfolio-note">Portfolio note</a></p>
  </header>
  <main>
    <section class="kpis">
      <div class="card"><div class="metric-label">Collections</div><div class="metric-value">{collection_count}</div></div>
      <div class="card"><div class="metric-label">Average readiness</div><div class="metric-value">{avg_readiness:.1f}</div></div>
      <div class="card"><div class="metric-label">At-risk launches</div><div class="metric-value">{at_risk}</div></div>
      <div class="card"><div class="metric-label">Open critical risks</div><div class="metric-value">{open_critical}</div></div>
    </section>

    <h2 id="business-view">Business View</h2>
    <p>This static page is designed for GitHub Pages and recruiter review. It summarizes the same synthetic scenario dataset used by the Streamlit dashboard, without requiring a local app server or external credentials.</p>

    <section class="grid">
      <div class="card">
        <h2>Readiness Bands</h2>
        {bar_rows(band_items)}
      </div>
      <div class="card">
        <h2>Delay by Workstream</h2>
        {bar_rows(workstream_items, "d")}
      </div>
      <div class="card">
        <h2>Supplier Delay Watchlist</h2>
        {bar_rows(supplier_items, "d")}
      </div>
      <div class="card">
        <h2>Portfolio Scope</h2>
        <p>{order_count} purchase orders, {len(milestones)} milestones, {len(risks)} risks, {len(actions)} mitigation actions, and {supplier_count} representative suppliers are connected through collection IDs and supplier IDs.</p>
      </div>
    </section>

    <h2 id="lowest-readiness">Lowest Readiness Collections</h2>
    <table>
      <thead><tr><th>Collection</th><th>Brand</th><th>Market</th><th>Readiness</th><th>Band</th></tr></thead>
      <tbody>{top_rows}</tbody>
    </table>

    <h2 id="portfolio-note">Portfolio Note</h2>
    <p class="note">The data is synthetic scenario data generated from public fashion portfolio context. It is not confidential company data and does not represent official operational records from any retailer.</p>
  </main>
</body>
</html>
"""
    (DOCS / "index.html").write_text(html_doc, encoding="utf-8")


if __name__ == "__main__":
    main()
