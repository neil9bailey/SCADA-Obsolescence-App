# SCADA Lifecycle Command Centre

A runnable full-stack MVP that converts a static SCADA obsolescence register into a live portfolio and delivery application.

The application keeps the asset baseline, risk assessment and programme packages as linked database records. Asset changes immediately recalculate the risk score, risk band, recommended delivery wave and data-completeness measure.

![Dashboard preview](scada-dashboard.png)

## What is included

- Live portfolio dashboard with risk, lifecycle, funding and evidence-quality indicators
- Searchable and filterable asset register
- Asset create, edit and delete workflows
- Transparent 0–100 risk assessment and recommended intervention wave
- Programme packages with delivery gate, target wave, budget, contingency, target state, outage and dependency fields
- CSV import with upsert by `asset_code`, row validation and error reporting
- CSV export of the current relational register
- Audit-event history for create, update, delete and import actions
- REST API and interactive OpenAPI documentation
- SQLite for a one-command demonstration
- PostgreSQL-compatible SQLAlchemy model and Docker Compose deployment
- Alembic migration support
- Automated API tests
- Fictional seed data, clearly identified in the user interface

## Guides and assessment evidence

- Full operator/developer guide: `docs/SOLUTION_GUIDE.md`
- Current code assessment, verification evidence and issue register: `docs/ASSESSMENT_REPORT.md`
- Field-level import and validation reference: `docs/DATA_DICTIONARY.md`

## Architecture

```text
Browser SPA
    │  same-origin Fetch API
    ▼
FastAPI REST service + static UI
    │
    ▼
SQLAlchemy ORM
    │
    ├── SQLite for local evaluation
    └── PostgreSQL for managed deployment
```

The browser has no direct OT connectivity. Data should enter through an approved export, integration service or controlled transfer route.

## Quick start

Python 3.11 or later is recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- Application: `http://localhost:8000`
- API documentation: `http://localhost:8000/api/docs`
- Health endpoint: `http://localhost:8000/api/health`

The default database is `data/scada_obsolescence.db`. The application loads fictional demonstration records when the database is empty and `SEED_DEMO=true`.

To start with an empty register:

```bash
SEED_DEMO=false uvicorn app.main:app --reload
```

## Docker and PostgreSQL

```bash
cp .env.example .env
# Set SCADA_DB_PASSWORD in your shell or deployment secret store.
docker compose up --build
```

Docker Compose starts the application and PostgreSQL. For a governed environment, replace the supplied password default, use a managed database service, disable demonstration seeding and put the application behind enterprise authentication and TLS.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file in `DATA_DIR` | SQLAlchemy connection URL |
| `DATA_DIR` | `./data` | SQLite and local data directory |
| `SEED_DEMO` | `true` | Load fictional data when the asset table is empty |
| `AUTO_CREATE_SCHEMA` | `true` | Create missing tables at startup for evaluation |
| `APP_NAME` | SCADA Lifecycle Command Centre | Application display name |

For controlled deployments, apply Alembic migrations and set `AUTO_CREATE_SCHEMA=false`.

```bash
export DATABASE_URL='postgresql+psycopg://user:password@host:5432/scada_lifecycle'
alembic upgrade head
AUTO_CREATE_SCHEMA=false SEED_DEMO=false uvicorn app.main:app
```

## Risk model

Each 1–5 rating is normalized and weighted. Unknown lifecycle status is rated as elevated exposure, and weak evidence confidence adds a visible penalty.

| Factor | Weight |
|---|---:|
| Business criticality | 15% |
| Safety impact | 10% |
| Production impact | 10% |
| Vendor support status | 20% |
| Cyber exposure | 15% |
| Failure likelihood | 10% |
| Spares risk | 5% |
| Recoverability risk | 10% |
| Dependency complexity | 5% |

Evidence-confidence penalties are A: 0, B: 2, C: 5 and D: 8 points, capped at 100.

| Score | Band |
|---:|---|
| 80–100 | Critical |
| 60–79.9 | High |
| 40–59.9 | Medium |
| Below 40 | Low |

Recommended response:

- High or critical risk with delivery readiness 1–2: **Wave 0**, contain and accelerate definition
- High or critical risk with readiness 3–5: **Wave 1**
- Medium risk: **Wave 2**
- Low risk: **Monitor**

The model is deliberately kept in `app/services/risk.py` so governance can approve and version it without rewriting the UI.

## CSV migration

Use the **Data exchange** page or POST a UTF-8 CSV to `/api/assets/import`.

Minimum columns for a new record:

```text
asset_code,system_name,site
```

The sample file at `data/sample-import.csv` demonstrates the full structure. See `docs/DATA_DICTIONARY.md` for field definitions and validation rules. Existing `asset_code` values are updated. `programme_code` can be used to link an asset to an existing package. Calculated fields such as `risk_score` are ignored and regenerated by the backend.

The importer uses a database savepoint for each row. A malformed row is reported without discarding valid rows in the same file.

## API examples

Create an asset:

```bash
curl -X POST http://localhost:8000/api/assets \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_code": "SITE-PLC-101",
    "system_name": "Transfer pumping PLC",
    "site": "North Site",
    "asset_type": "PLC",
    "support_status": "limited",
    "business_criticality": 5,
    "safety_impact": 4,
    "production_impact": 5,
    "cyber_exposure": 3,
    "failure_likelihood": 3,
    "spares_risk": 4,
    "recoverability_risk": 4,
    "dependency_complexity": 3,
    "evidence_confidence": "B",
    "delivery_readiness": 2,
    "treatment": "upgrade"
  }'
```

Query high-risk assets:

```bash
curl 'http://localhost:8000/api/assets?risk_band=Critical&sort_by=risk_score&sort_dir=desc'
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q tests
```

The tests cover health, dashboard rollups, asset CRUD and recalculation, programme linkage, funding aggregation, row-isolated CSV import and export.

## Production hardening before operational use

This MVP intentionally leaves enterprise-specific controls outside the codebase. Add these before placing real portfolio data into service:

1. Enterprise SSO, role-based authorization and named-user audit attribution
2. TLS termination, managed secrets and a restricted deployment network zone
3. Managed PostgreSQL with encryption, backups, restore tests and retention policy
4. Alembic-only schema change control, release promotion and rollback procedures
5. Central audit and security logging to the monitoring platform
6. Attachment storage for supplier notices, architecture diagrams and recovery evidence
7. Approval workflow for risk acceptance, treatment selection and programme gates
8. Fine-grained data ownership by business unit or site where required
9. Integration through read-only CMDB, EAM or controlled staging interfaces, never direct active discovery against production OT
10. Vulnerability management, dependency scanning, penetration testing and secure SDLC controls

## MVP boundaries

- Authentication and authorization are not included
- Audit events currently use a generic application actor
- No document attachments or approval signatures
- No direct CMDB, EAM, ERP or supplier-lifecycle connector
- No automatic collection from SCADA, PLC or network devices
- Risk weighting is configurable in code, not yet through a governed administration screen

These are deliberate seams for the next delivery increment rather than hidden assumptions in the data model.
