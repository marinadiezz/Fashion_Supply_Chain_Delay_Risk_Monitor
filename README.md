# Fashion Supply Chain Delay & Risk Monitor

One-sentence summary: a synthetic analytics project that monitors launch readiness, supplier delay risk, operational blockers, and mitigation ownership for a multi-brand fashion supply chain.

## Problem Statement

Fashion launches depend on many connected activities: supplier confirmation, production, quality checks, logistics, warehouse allocation, product content, and market launch readiness. A delay in one workstream can quickly affect downstream launch dates. This project turns those dependencies into a practical control-tower style dashboard for weekly PMO, operations, and analytics review.

## Business Value

The project helps answer four operational questions:

- Which collections are ready, at risk, or critical before launch?
- Which workstreams and suppliers are creating the most delay pressure?
- Which risks, blockers, and mitigation actions need escalation?
- How should a project or operations lead prioritize the next launch review?

It is designed for portfolio review by Data Analyst, Data Scientist, Data Engineer, Product/Project Analyst, PMO, and Operations audiences.

## Tools And Technologies

- Python
- pandas and NumPy
- Streamlit
- Plotly
- Jupyter notebooks
- CSV-based data model
- Static HTML for GitHub Pages

## Dataset

The data in this repository is synthetic scenario data generated for portfolio demonstration. It uses public fashion brand and sourcing context for realism, but the line-level purchase orders, milestones, incidents, risks, suppliers, and mitigation actions are not confidential company records.

Current modeled scope:

- 30 collection launch scenarios
- 34 representative suppliers
- 390 purchase orders
- 540 milestones
- 190 risks
- 165 incidents
- 240 mitigation actions

The sample CSV files in `data/raw/` and `data/processed/` are safe to publish as synthetic project data. Do not add private company exports or local databases to this repository.

## Methodology

1. Generate synthetic fashion launch data from public portfolio context and fixed random seeds.
2. Transform raw records into enriched operational tables.
3. Calculate readiness, delay, supplier, risk, blocker, and mitigation KPIs.
4. Present the results in an interactive Streamlit dashboard.
5. Publish a static GitHub Pages summary for recruiters who do not run the app locally.

## Key Features

- Executive readiness overview with launch health KPIs
- Delay analysis by workstream, collection, and purchase order
- Risk severity and exposure scoring
- Supplier performance scorecard and watchlist
- Sourcing geography view in the Streamlit app
- Launch timeline and dependency review
- Mitigation action board
- Scenario simulator for directional PMO discussion
- Static `docs/index.html` page for GitHub Pages

## Main Insights

- Low-readiness launches usually combine blocked milestones, overdue actions, and unresolved high-severity risks.
- Supplier reliability and lead-time variance affect launch readiness, not only procurement performance.
- E-commerce, logistics, quality, and warehouse tasks become more critical as launch dates approach.
- A useful PMO view should connect signal to ownership: what is blocked, who owns it, which supplier is involved, and what mitigation is due.

## Screenshots

Static recruiter previews are stored in `assets/screenshots/`.

![Executive overview](assets/screenshots/executive_overview.svg)

![Supplier watchlist](assets/screenshots/supplier_watchlist.svg)

![Risk monitoring](assets/screenshots/risk_monitoring.svg)

## How To Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/generate_data.py
python src/transform_data.py
python src/build_static_portfolio.py
streamlit run app/streamlit_app.py
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## How To View The HTML Dashboard

The interactive dashboard is a Streamlit app, so it requires a local Streamlit server.

For GitHub portfolio browsing, use the static HTML artifact:

- Open `docs/index.html` directly in a browser, or
- Publish the `docs/` folder with GitHub Pages.

The static page has no loopback-server dependency, browser-only local file URL dependency, machine-specific absolute paths, API keys, or external data fetches. It embeds a recruiter-friendly summary generated from the synthetic processed CSVs.

## How Reviewers Can Open This Project

This repository includes two different ways to review the work: a static GitHub Pages page and the full interactive Streamlit app. They serve different purposes.

### Option 1: View The Static Portfolio Page

Best for: recruiters, hiring managers, and reviewers who want a quick two-minute overview without installing anything.

The file `docs/index.html` is a static portfolio page generated from the processed synthetic data. It can be opened directly from the repository and can also be published with GitHub Pages.

What this option shows:

- Project summary
- Main portfolio KPIs
- Readiness bands
- Delay pressure by workstream
- Supplier delay watchlist
- Lowest-readiness collections
- Clear note that the data is synthetic and non-confidential

What this option does not show:

- Full Streamlit interactivity
- Sidebar filters
- Dynamic Plotly exploration
- Scenario simulator interactions

To publish it with GitHub Pages:

1. Push this repository to GitHub.
2. Open the repository on GitHub.
3. Go to `Settings`.
4. Go to `Pages`.
5. Under `Build and deployment`, choose `Deploy from a branch`.
6. Select the main branch.
7. Select the `/docs` folder.
8. Save the configuration.

After GitHub finishes publishing, the project will have a public web page in this format:

```text
https://your-github-username.github.io/fashion-supply-chain-delay-risk-monitor/
```

This is the best link to place near the top of the README once the repository is published.

### Option 2: Run The Full Streamlit App Locally

Best for: technical reviewers who want to inspect the full interactive dashboard.

Streamlit apps are Python applications. They do not run as plain HTML files inside GitHub. To open the full dashboard, a reviewer needs to clone the repository, install the dependencies, and run the app.

Steps:

```bash
git clone https://github.com/your-github-username/fashion-supply-chain-delay-risk-monitor.git
cd fashion-supply-chain-delay-risk-monitor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/generate_data.py
python src/transform_data.py
streamlit run app/streamlit_app.py
```

On macOS or Linux, use this activation command instead:

```bash
source .venv/bin/activate
```

After running the Streamlit command, Streamlit will print a local browser URL in the terminal. Open that URL to use the full app.

### Option 3: Deploy The Interactive App Publicly With Streamlit Community Cloud

Best for: portfolio sharing when you want reviewers to open the full interactive app from a public link.

GitHub Pages is useful for the static page, but it cannot host a Python Streamlit application. To make the complete dashboard publicly available, deploy it with Streamlit Community Cloud.

Steps:

1. Push this repository to GitHub.
2. Go to Streamlit Community Cloud.
3. Sign in with GitHub.
4. Create a new app.
5. Select this repository.
6. Select the main branch.
7. Set the app entry point to:

```text
app/streamlit_app.py
```

8. Confirm that `requirements.txt` is in the repository root.
9. Deploy the app.

Once deployed, Streamlit will provide a public app link. Add that link near the top of this README using this format:

```markdown
View the interactive dashboard: https://your-streamlit-app-url.streamlit.app
View the static portfolio page: https://your-github-username.github.io/fashion-supply-chain-delay-risk-monitor/
```

### Recommended Portfolio Setup

For a professional GitHub portfolio, use both links:

- GitHub Pages link for the fast static overview.
- Streamlit Community Cloud link for the full interactive dashboard.

This gives non-technical reviewers a quick path and technical reviewers a deeper path.

## Repository Structure

```text
fashion-supply-chain-delay-risk-monitor/
|-- README.md
|-- .gitignore
|-- requirements.txt
|-- app/
|   |-- components.py
|   |-- streamlit_app.py
|   `-- style.css
|-- assets/
|   `-- screenshots/
|-- data/
|   |-- raw/
|   `-- processed/
|-- docs/
|   `-- index.html
|-- notebooks/
|   |-- 01_data_generation_validation.ipynb
|   `-- 02_eda_kpi_logic.ipynb
|-- outputs/
`-- src/
    |-- build_static_portfolio.py
    |-- calculate_kpis.py
    |-- generate_data.py
    |-- risk_scoring.py
    |-- transform_data.py
    `-- utils.py
```

## Publication Notes

Keep in GitHub:

- Source code in `src/` and `app/`
- Synthetic sample CSVs in `data/raw/` and `data/processed/`
- Notebooks in `notebooks/`
- Static portfolio page in `docs/index.html`
- Recruiter previews in `assets/screenshots/`
- `README.md`, `requirements.txt`, and `.gitignore`

Do not upload:

- `.venv/`, `venv/`, or other local environments
- `__pycache__/`, `.ipynb_checkpoints/`, and cache folders
- `.env`, credentials, API keys, tokens, passwords, or secrets
- Local databases such as `.db`, `.sqlite`, or `.duckdb`
- Private company exports or confidential raw data
- Temporary Office files such as `~$*.docx` or generated junk

## Limitations

- The records are scenario data, not live ERP, PLM, WMS, logistics, or order-management data.
- The scenario simulator is directional and should not be interpreted as a predictive model.
- Supplier names are representative scenario entities, not disclosed legal suppliers.
- Cost and margin impact are represented through exposure bands rather than detailed financial statements.
- The static HTML page is a portfolio summary; the full interactive experience is in Streamlit.

## Future Improvements

- Add automated dashboard screenshot capture.
- Add a small test suite for KPI and readiness scoring functions.
- Add configurable scenario assumptions for different launch calendars.
- Add exportable weekly review packs for PMO stakeholders.
- Add role-specific views for sourcing, logistics, merchandising, and leadership.

## Contact / Portfolio Note

This project is prepared as a public GitHub portfolio case study. It demonstrates analytics product thinking, data modeling, KPI design, operational storytelling, and dashboard implementation using non-confidential synthetic data.
