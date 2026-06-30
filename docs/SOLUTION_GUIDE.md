# SCADA Lifecycle Command Centre guide

This guide explains how to understand, run, operate, test, and extend the SCADA Lifecycle
Command Centre MVP.

The application turns a static SCADA obsolescence register into a live lifecycle portfolio.
It stores assets, risk evidence, intervention packages, budgets, dependencies, audit events,
and CSV exchange history in a relational database behind a FastAPI service and a browser UI.

## 1. What the solution does

Use this application to:

- Maintain a controlled SCADA, OT, and industrial control asset register.
- Calculate a 0-100 obsolescence and resilience risk score for every asset.
- Group related assets into programme packages with budgets, dependencies, waves, and gates.
- Track evidence quality, owner gaps, lifecycle gaps, and unassigned assets.
- Import a controlled CSV register and export the current live register.
- Review audit events for create, update, delete, import, and seed actions.
- Demonstrate a fictional portfolio without connecting to real production OT systems.

Do not use this MVP as a direct active-discovery tool against SCADA, PLC, RTU, network, or
historian environments. Data should arrive through a controlled export, staging process, or
approved integration path.

## 2. Repository map

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app, static UI mount, startup schema/seed flow, security headers |
| `app/config.py` | Environment-based runtime settings |
| `app/db.py` | SQLAlchemy engine, session factory, SQLite foreign-key enforcement |
| `app/models.py` | SQLAlchemy ORM tables for assets, programmes, and audit events |
| `app/schemas.py` | Pydantic request and response models |
| `app/services/risk.py` | Risk scoring, risk band, recommended wave, completeness calculation |
| `app/services/audit.py` | Audit event helper |
| `app/routers/assets.py` | Asset CRUD, filters, CSV import, CSV export, facets |
| `app/routers/programmes.py` | Programme package CRUD and rollups |
| `app/routers/dashboard.py` | Portfolio summary, distributions, quality indicators, activity |
| `app/routers/health.py` | Database reachability check |
| `app/static/` | Dependency-free browser SPA |
| `migrations/` | Alembic migration environment and initial schema |
| `tests/` | FastAPI API regression tests |
| `data/sample-import.csv` | Example CSV import template |
| `docs/DATA_DICTIONARY.md` | Field-level data dictionary and import rules |
| `Dockerfile` | Production-style Python image for the FastAPI app |
| `docker-compose.yml` | App plus PostgreSQL deployment for evaluation |
| `.env.example` | Local configuration template |

## 3. Core concepts

### Assets

An asset is a SCADA, OT, or industrial control item with identity, lifecycle, technical,
risk, accountability, and programme-link fields. Key identifiers are:

- `asset_code`: stable unique identifier and CSV upsert key.
- `system_name`: human-readable asset or system name.
- `site`: primary location.
- `programme_id`: optional database link to a programme package.
- `programme_code`: optional CSV-only link to an existing programme package.

The backend owns calculated fields:

- `risk_score`
- `risk_band`
- `recommended_wave`
- `data_completeness`
- timestamps

Do not import or manually edit calculated values. They are regenerated when an asset is
created, updated, or imported.

### Programme packages

A programme package groups related assets into an investable delivery scope. It carries:

- package code and title
- owner and sponsor
- delivery status
- target wave
- budget estimate and contingency
- target dates
- outage window
- target platform or target state
- dependencies and notes

The API derives package rollups from linked assets:

- `asset_count`
- `critical_assets`
- `average_risk`
- `total_budget`

### Audit events

Audit events capture application actions with a summary, entity type, entity id, actor, and
timestamp. The current MVP uses a generic application actor because authentication is not yet
implemented.

## 4. Risk model

Risk is calculated in `app/services/risk.py`.

Each rating is normalized from 1-5 and multiplied by its weight:

| Factor | Weight |
|---|---:|
| Business criticality | 15 |
| Safety impact | 10 |
| Production impact | 10 |
| Support status | 20 |
| Cyber exposure | 15 |
| Failure likelihood | 10 |
| Spares risk | 5 |
| Recoverability risk | 10 |
| Dependency complexity | 5 |

Support status is mapped internally:

| Support status | Rating |
|---|---:|
| `supported` | 1 |
| `limited` | 3 |
| `end_of_support` | 5 |
| `unknown` | 4 |

Evidence confidence adds a penalty:

| Confidence | Meaning | Penalty |
|---|---|---:|
| `A` | Authoritative evidence | 0 |
| `B` | Verified internally | 2 |
| `C` | Inferred | 5 |
| `D` | Unknown or unverified | 8 |

Risk bands:

| Score | Band |
|---:|---|
| 80-100 | Critical |
| 60-79.9 | High |
| 40-59.9 | Medium |
| Below 40 | Low |

Recommended wave:

| Condition | Recommendation |
|---|---|
| Score >= 60 and readiness <= 2 | Wave 0 |
| Score >= 60 and readiness >= 3 | Wave 1 |
| Score >= 40 | Wave 2 |
| Score < 40 | Monitor |

## 5. Local quick start

Python 3.11 or later is recommended. Python 3.12 was used during the latest assessment.

### Windows PowerShell

```powershell
cd F:\code\SCADA-Obsolescence-App
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open:

- Application: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/api/docs`
- Health check: `http://127.0.0.1:8000/api/health`

If PowerShell script execution policy blocks activation, use the direct interpreter path shown
above instead of activating the virtual environment.

### macOS or Linux shell

```bash
cd /path/to/SCADA-Obsolescence-App
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## 6. Configuration

Configuration is read from environment variables in `app/config.py`.

| Variable | Default | Use |
|---|---|---|
| `APP_NAME` | `SCADA Lifecycle Command Centre` | App/API display name |
| `DATA_DIR` | `./data` | SQLite database location |
| `DATABASE_URL` | SQLite in `DATA_DIR` | SQLAlchemy connection URL |
| `SEED_DEMO` | `true` | Load fictional demo data when asset table is empty |
| `AUTO_CREATE_SCHEMA` | `true` | Create missing tables at startup |

Local empty-register example:

```powershell
$env:SEED_DEMO = "false"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Managed PostgreSQL-style example:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://scada_app:replace-me@db.example.internal:5432/scada_lifecycle"
$env:AUTO_CREATE_SCHEMA = "false"
$env:SEED_DEMO = "false"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app
```

For controlled deployments, prefer `AUTO_CREATE_SCHEMA=false` and apply Alembic migrations as
part of the release process.

## 7. Database and migrations

SQLite is the default local database. PostgreSQL is supported through SQLAlchemy and
`psycopg`.

Apply migrations:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Check model/schema drift after the database is at the current revision:

```powershell
.\.venv\Scripts\python.exe -m alembic check
```

Important: `alembic check` expects the target database to be upgraded. On a brand-new database,
run `alembic upgrade head` first.

## 8. Using the browser UI

### Portfolio dashboard

Use the dashboard for executive and portfolio-level review:

- total registered assets
- high and critical risk count
- unsupported and unknown-lifecycle count
- average risk
- active programme count
- funding estimate including contingency
- data completeness
- risk, support, programme, wave, and site distributions
- highest exposures
- recent activity

When `SEED_DEMO=true`, the dashboard displays a fictional-demo callout.

### Asset register

Use the asset register to search, filter, add, edit, and delete assets.

Common workflows:

1. Search by asset code, system name, manufacturer, model, or owner.
2. Filter by site, support status, risk band, or programme package.
3. Sort by risk score, asset code, site, or update time.
4. Open a row to edit identity, lifecycle evidence, ratings, owner, programme link, and notes.
5. Save to recalculate risk, recommended wave, and completeness.

Required asset fields:

- `asset_code`
- `system_name`
- `site`

### Programme packages

Use the programme page to convert asset-level risk into delivery scopes.

Package records include:

- package code
- title and problem statement
- owner and sponsor
- status/gate
- target wave
- budget estimate and contingency
- dates, outage window, target state, dependencies, notes

Click a package card to edit it. Deleting a package unassigns linked assets rather than
deleting the assets.

### Data exchange

Use the data exchange page to:

- download the current register as CSV
- download or inspect the sample template
- import a UTF-8 CSV
- review row-level import results

CSV import uses `asset_code` for upsert. Valid rows can be imported even if another row fails.

## 9. CSV import guide

Minimum columns for a new record:

```text
asset_code,system_name,site
```

Recommended controlled-import sequence:

1. Export or prepare a register outside the app.
2. Align column names with `docs/DATA_DICTIONARY.md`.
3. Use `programme_code` to link assets to existing packages.
4. Keep calculated fields out of the source register or accept that they will be ignored.
5. Import through the Data exchange page.
6. Review created, updated, failed, and row-error counts.
7. Export the live register for evidence or offline review.

Rules:

- Existing assets are matched by exact `asset_code`.
- Empty optional cells do not overwrite existing values during update.
- Rating fields must be integers from 1 to 5.
- `programme_code` must already exist.
- Direct `programme_id` imports must refer to an existing programme id.
- At most 25 row-level errors are returned in one response.

## 10. API guide

Interactive API docs are available at:

```text
http://127.0.0.1:8000/api/docs
```

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Dashboard:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/dashboard/summary
```

List assets:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/assets?risk_band=Critical&sort_by=risk_score&sort_dir=desc"
```

Create an asset:

```powershell
$body = @{
  asset_code = "SITE-PLC-101"
  system_name = "Transfer pumping PLC"
  site = "North Site"
  asset_type = "PLC"
  support_status = "limited"
  business_criticality = 5
  safety_impact = 4
  production_impact = 5
  cyber_exposure = 3
  failure_likelihood = 3
  spares_risk = 4
  recoverability_risk = 4
  dependency_complexity = 3
  evidence_confidence = "B"
  delivery_readiness = 2
  treatment = "upgrade"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/assets `
  -ContentType "application/json" `
  -Body $body
```

Create a programme package:

```powershell
$body = @{
  package_code = "OBP-010"
  title = "Telemetry upgrade package"
  status = "discovery"
  target_wave = "Wave 1"
  budget_estimate = 250000
  contingency_percent = 25
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/programmes `
  -ContentType "application/json" `
  -Body $body
```

Export CSV:

```powershell
Invoke-WebRequest `
  -Uri http://127.0.0.1:8000/api/assets/export.csv `
  -OutFile .\exported-scada-register.csv
```

Import CSV:

```powershell
$form = @{
  file = Get-Item .\data\sample-import.csv
}

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/assets/import `
  -Form $form
```

## 11. Docker and Compose

Render the Compose configuration:

```powershell
docker compose config
```

Build the app image:

```powershell
docker build -t scada-obsolescence-app:local .
```

Run app plus PostgreSQL:

```powershell
copy .env.example .env
# Edit .env or set SCADA_DB_PASSWORD in your environment.
docker compose up --build
```

Open:

- Application: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/api/docs`

Stop:

```powershell
docker compose down
```

For production-like use, replace the Compose password default, disable demo seeding, disable
startup schema creation, place the app behind TLS and enterprise authentication, and use managed
PostgreSQL with backups and restore testing.

## 12. Testing and verification

Install dev dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Run API tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

Run schema drift check on a fresh temporary database:

```powershell
$dbPath = Join-Path $env:TEMP "scada_obsolescence_alembic_check.db"
if (Test-Path $dbPath) { Remove-Item -LiteralPath $dbPath -Force }
$dbUrl = "sqlite+pysqlite:///" + ($dbPath -replace "\\", "/")
$env:DATABASE_URL = $dbUrl
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
```

Parse-check the browser JavaScript:

```powershell
node --check app\static\app.js
```

Manual browser smoke:

1. Start the app.
2. Open dashboard, asset register, programme packages, and data exchange.
3. Open Add asset, Edit asset, New programme package, and Edit programme package modals.
4. Confirm the browser console has no errors.

## 13. Production hardening checklist

Before handling real SCADA or OT lifecycle data, add or confirm:

- Enterprise SSO and role-based access control.
- Named-user audit attribution.
- TLS termination and secure headers appropriate to the hosting platform.
- Managed secret storage.
- Managed PostgreSQL with encryption, backups, restore tests, and retention policy.
- Alembic-only schema promotion, rollback, and release evidence.
- Approval workflow for risk acceptance, treatment, package gates, and closeout.
- Attachment/evidence storage for supplier notices, architecture diagrams, backups, and restore proof.
- Central application, audit, and security logging.
- Dependency and container vulnerability scanning.
- Penetration testing and secure SDLC controls.
- Controlled integration with CMDB, EAM, ERP, or staging data sources.
- Explicit ban on direct active discovery against production OT from this app.

## 14. Troubleshooting

### `ModuleNotFoundError: No module named 'fastapi'`

Install dependencies in the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### `alembic check` says the target database is not up to date

Run migrations first:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
```

### Demo data appears unexpectedly

Set:

```powershell
$env:SEED_DEMO = "false"
```

Then start against an empty database.

### The app starts but tables are missing

For local evaluation, keep:

```powershell
$env:AUTO_CREATE_SCHEMA = "true"
```

For controlled deployments, run Alembic migrations and set:

```powershell
$env:AUTO_CREATE_SCHEMA = "false"
```

### CSV import reports unknown `programme_code`

Create the programme package first, or remove the `programme_code` value from the CSV row.

### CSV import reports invalid rating

Check all rating fields are integers from 1 to 5.

## 15. Extension guidance

Keep these boundaries intact unless an architecture decision approves a change:

- The browser UI talks to the FastAPI API only.
- The browser has no direct OT or database connectivity.
- Risk scoring lives in `app/services/risk.py`.
- Calculated fields are backend-owned.
- CSV import is controlled, validated, and row-isolated.
- Alembic owns controlled schema evolution for non-local deployments.

Likely next increments:

- Authentication and RBAC.
- Named-user audit.
- Evidence attachment storage.
- Package approval workflow.
- Frontend E2E test suite.
- Risk-model versioning and governance screen.
- Managed deployment runbook.
