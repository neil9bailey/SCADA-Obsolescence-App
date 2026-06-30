# Code assessment report

Assessment date: 2026-06-30

Repository: `F:\code\SCADA-Obsolescence-App`

Assessment scope:

- Familiarise with the solution and source material.
- Check backend, frontend, database, migration, test, and deployment paths.
- Create a practical guide/how-to.
- Identify and fix clear, safe bugs found during assessment.
- Preserve the existing FastAPI, SQLAlchemy, SQLite/PostgreSQL, and dependency-free SPA design.

## Executive summary

The repository contains a runnable full-stack MVP for a SCADA obsolescence lifecycle portfolio.
The core architecture is coherent and matches the creator notes:

- FastAPI REST backend.
- SQLAlchemy 2.0 ORM.
- SQLite default with PostgreSQL-ready `DATABASE_URL`.
- Alembic migration baseline.
- Dependency-free browser SPA.
- Fictional seed portfolio.
- Asset CRUD, programme CRUD, dashboard rollups, audit events, CSV import/export, and risk scoring.
- Dockerfile and Docker Compose deployment path.

During assessment, three confirmed validation/data-integrity defects were found and fixed:

1. Blank asset identity updates could produce a 500 response and persist an invalid row.
2. Blank-looking programme package codes and titles were accepted.
3. `programme_id=0` and some direct CSV programme-id inputs could bypass intended relationship checks, especially on SQLite.

After the fixes, automated tests pass, dependency audits are clean, Alembic reports no
model/schema drift after upgrade, the SPA views load without console errors, Docker Compose
renders, the Docker image builds, and the container smoke test returns healthy status with
seeded demo data.

## Governance and intake notes

The repo includes `AGENTS.md` and local role files under `agents/`. The requested work was run
as the governed engineering organisation:

- G0 intake: human-approved repo assessment and documentation epic.
- G2 implementation: narrow validation/data-integrity fixes and documentation.
- G3 verification: tests, migration check, API probes, browser checks, Docker checks.
- G4 UAT: browser journey smoke was performed, but real end-user acceptance remains outstanding.
- G5 security: security posture reviewed at MVP level; production controls remain required.
- G6 release: human decision only.

No `agent-team/ORCHESTRATOR.md` or `agent-team/registry.json` folder exists in this repository.
The connected `agentTeam` MCP server and the local `agents/` role files were used instead.

This directory is not currently a Git repository, so there is no branch, commit history, or git
diff metadata to inspect.

## Source material reviewed

Reviewed files and areas:

- `AGENTS.md`
- `agents/delivery-lead.md`
- `agents/principal-engineer.md`
- `README.md`
- `docs/DATA_DICTIONARY.md`
- `SCADA Obsolescence Transformation Framework.docx`
- `requirements.txt`
- `requirements-dev.txt`
- `Dockerfile`
- `docker-compose.yml`
- `Makefile`
- `alembic.ini`
- `migrations/env.py`
- `migrations/versions/f2e35d38f616_initial_schema.py`
- `tests/conftest.py`
- `tests/test_api.py`
- `app/main.py`
- `app/config.py`
- `app/db.py`
- `app/models.py`
- `app/schemas.py`
- `app/seed.py`
- `app/services/risk.py`
- `app/services/audit.py`
- `app/routers/assets.py`
- `app/routers/programmes.py`
- `app/routers/dashboard.py`
- `app/routers/health.py`
- `app/static/index.html`
- `app/static/app.js`
- `app/static/styles.css`
- `data/sample-import.csv`

The Word framework document aligns with the MVP intent: move from static obsolescence register
to governed, evidence-led lifecycle portfolio with programme packages, investment waves, and
Wave 0 containment for the highest-risk systems.

## Solution architecture

```text
Browser SPA
  -> same-origin fetch calls
FastAPI app
  -> routers for health, dashboard, assets, programmes
SQLAlchemy ORM
  -> SQLite for local evaluation
  -> PostgreSQL through DATABASE_URL for managed deployment
Alembic
  -> controlled schema baseline and drift checks
```

Runtime startup:

1. `app.main` builds the FastAPI application.
2. If `AUTO_CREATE_SCHEMA=true`, `init_db()` creates missing tables.
3. If `SEED_DEMO=true`, `seed_demo_data()` loads fictional records only when the asset table is empty.
4. Static UI is served from `app/static`.
5. API docs are served at `/api/docs`.

## Data model summary

Main tables:

- `assets`: identity, lifecycle, risk ratings, treatment, owner, notes, calculated risk fields, optional programme link.
- `programmes`: package identity, delivery status, target wave, budget, dates, outage, target state, dependencies.
- `audit_events`: event stream for system and CRUD/import actions.

Key relationships:

- `assets.programme_id` references `programmes.id`.
- Programme delete unassigns linked assets.
- SQLite foreign keys are now explicitly enabled at connection time.

## Risk model summary

The risk model is implemented in `app/services/risk.py`.

Inputs:

- business criticality
- safety impact
- production impact
- support status
- cyber exposure
- failure likelihood
- spares risk
- recoverability risk
- dependency complexity
- evidence confidence
- delivery readiness

Outputs:

- `risk_score`
- `risk_band`
- `recommended_wave`
- `data_completeness`

Unknown support and weak evidence are deliberately treated as elevated exposure.

## Confirmed bugs found and fixed

### 1. Blank asset update caused 500 and persisted invalid data

Evidence before fix:

- API probe created an asset, then patched `asset_code` to spaces.
- `PATCH /api/assets/{id}` returned `500 Internal Server Error`.
- `GET /api/assets/{id}` also returned `500 Internal Server Error` after the bad update.
- Server stack trace showed FastAPI response validation failing because the response schema
  stripped the blank string to `None`.

Fix:

- Added consistent string stripping to `AssetUpdate`.
- Added model validation that prevents clearing required asset identity fields:
  `asset_code`, `system_name`, and `site`.
- Added regression coverage.

Post-fix evidence:

- `PATCH` with spaces returns `422`.
- Follow-up `GET` returns the original valid asset.

### 2. Blank-looking programme package identity accepted

Evidence before fix:

- `POST /api/programmes` with `package_code="   "` and `title="   "` returned `201 Created`.

Fix:

- Added string stripping to `ProgrammeBase` and `ProgrammeUpdate`.
- Added model validation that prevents clearing required programme identity fields:
  `package_code` and `title`.
- Added regression coverage.

Post-fix evidence:

- Blank-looking package create returns `422`.
- Blank-looking package update returns `422`.

### 3. Invalid programme links could bypass checks

Evidence before fix:

- `POST /api/assets` with `programme_id=0` returned `201 Created`.
- CSV import could accept direct unknown programme ids in SQLite paths not covered by the
  `programme_code` lookup.

Fix:

- Added `ge=1` validation to asset `programme_id` fields.
- Changed router checks from truthiness checks to explicit `is not None` style existence checks.
- Added programme existence checks inside CSV import after Pydantic validation.
- Enabled SQLite foreign-key enforcement with `PRAGMA foreign_keys=ON`.
- Added regression coverage.

Post-fix evidence:

- `programme_id=0` returns `422`.
- Missing direct programme ids return `400` or row-level CSV import failure.
- SQLite now enforces foreign-key constraints.

## Other issue and risk findings

### High priority before real operational use

- No authentication or authorization is implemented.
- Audit actor is generic, not tied to named users.
- No approval workflow exists for risk acceptance, package gates, treatment changes, or closure.
- No evidence attachment storage exists for supplier notices, topology diagrams, backups, or restore proof.
- Docker Compose includes a password default suitable only for evaluation.
- `AUTO_CREATE_SCHEMA=true` is useful locally but should be disabled in controlled deployments.

### Medium priority

- Frontend verification is manual/browser-smoke only; no committed E2E suite exists.
- There is no committed CI workflow for dependency or container vulnerability scanning.
- There is no central logging or structured security/audit export.
- There is no documented backup/restore runbook for PostgreSQL deployment.
- The risk model is code-configured rather than governed through versioned admin screens.

### Low priority / hygiene

- The folder is not a Git repository, so normal branch, diff, and commit hygiene could not be assessed.
- A `.dockerignore` was missing and has been added to keep local caches, venvs, databases,
  tests, docs, and source documents out of image build context.

## Verification evidence

### Dependency setup

Initial test attempt with the system Python failed because dependencies were not installed:

```text
ModuleNotFoundError: No module named 'fastapi'
```

Resolution:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Result: dependencies installed successfully in the local ignored virtual environment.

### API regression tests

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

Result:

```text
7 passed in 3.91s
```

Coverage includes:

- health
- empty dashboard
- asset create/update/delete and risk recalculation
- validation rejection for blank asset identity fields
- invalid programme id rejection
- programme linkage and dashboard rollup
- blank programme identity rejection
- CSV row savepoints and export
- CSV unknown direct programme id rejection

### Dependency and vulnerability audit

Initial runtime audit found known vulnerabilities in:

- `python-multipart 0.0.29`
- transitive `starlette 0.50.0`

Initial dev audit also found a known vulnerability in:

- `pytest 9.0.2`

Fixes applied:

- `fastapi` upgraded to `0.138.2`.
- `starlette` pinned to `1.3.1`.
- `python-multipart` upgraded to `0.0.32`.
- `pytest` upgraded to `9.0.3`.
- `requirements-dev.txt` now uses `httpx2==2.5.0`, matching the current Starlette test-client path.

Final audit commands used absolute requirement-file paths to avoid Windows temp-path issues:

```powershell
$req = (Resolve-Path "requirements.txt").Path
.\.venv\Scripts\python.exe -m pip_audit --progress-spinner off -r $req

$devReq = (Resolve-Path "requirements-dev.txt").Path
.\.venv\Scripts\python.exe -m pip_audit --progress-spinner off -r $devReq
```

Final result for both runtime and dev requirements:

```text
No known vulnerabilities found
```

Dependency consistency:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Result:

```text
No broken requirements found.
```

### Alembic migration and drift check

Plain `alembic check` against a not-yet-upgraded target failed as expected:

```text
FAILED: Target database is not up to date.
```

Fresh upgraded temp database command:

```powershell
$dbPath = Join-Path $env:TEMP "scada_obsolescence_alembic_check.db"
if (Test-Path $dbPath) { Remove-Item -LiteralPath $dbPath -Force }
$dbUrl = "sqlite+pysqlite:///" + ($dbPath -replace "\\", "/")
$env:DATABASE_URL = $dbUrl
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
```

Result:

```text
No new upgrade operations detected.
```

### Live API smoke

Temporary server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Post-fix probe results:

```text
GET /api/health -> 200, database reachable
GET /api/dashboard/summary -> 200, total_assets=20
POST /api/assets with programme_id=0 -> 422
PATCH /api/assets/{id} with blank asset_code -> 422
GET /api/assets/{id} after rejected patch -> 200 with original asset_code
POST /api/programmes with blank package_code/title -> 422
```

### Frontend syntax and browser smoke

JavaScript parse check:

```powershell
node --check app\static\app.js
```

Result: passed with no output.

Browser checks against `http://127.0.0.1:8765`:

- Dashboard loaded.
- Asset register loaded.
- Programme packages loaded.
- Data exchange loaded.
- Add asset modal opened.
- Edit asset modal opened.
- New programme package modal opened.
- Edit programme package modal opened.
- Browser console error log was empty.

### Docker and deployment smoke

Compose render:

```powershell
docker compose config
```

Result: rendered successfully.

Final image build after dependency security updates:

```powershell
docker build -t scada-obsolescence-app:codex-check .
```

Result: build completed successfully.

After adding `.dockerignore`, the Docker build context was reduced to approximately 2 KB and
the image rebuilt successfully.

Final container smoke:

```powershell
docker run --rm -d -p 8766:8000 --name scada-codex-check scada-obsolescence-app:codex-check
```

Health and dashboard result:

```text
container=206b4a91ee66d851de398a27bb58b360985ae09c92ee88d145ffda6c4b901552 status=ok database=reachable total_assets=20
```

The container was stopped after the smoke test.

## Files changed during assessment

- Added `.dockerignore`.
- Added `docs/SOLUTION_GUIDE.md`.
- Added `docs/ASSESSMENT_REPORT.md`.
- Updated `README.md`.
- Updated `Makefile`.
- Updated `app/db.py`.
- Updated `app/routers/assets.py`.
- Updated `app/schemas.py`.
- Updated `requirements.txt`.
- Updated `requirements-dev.txt`.
- Updated `tests/test_api.py`.

## Recommended next work

1. Add authentication, RBAC, and named-user audit.
2. Add approval workflow for risk acceptance and programme gates.
3. Add evidence attachment storage and retention rules.
4. Add frontend E2E tests for core user journeys.
5. Add dependency/container scanning in CI.
6. Add a production deployment and backup/restore runbook.
7. Version the risk model and require governance approval for weighting changes.
8. Turn the current human/browser smoke into formal UAT scripts with named users and evidence.
