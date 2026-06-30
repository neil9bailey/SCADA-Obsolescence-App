# Data dictionary

## Asset register

| Field | Type / rule | Purpose |
|---|---|---|
| `asset_code` | Required string, unique, max 80 | Persistent identifier used for CSV upsert |
| `system_name` | Required string, max 200 | Human-readable system or maintainable asset name |
| `site` | Required string, max 120 | Primary operational location |
| `process_area` | Optional string | Process, building or functional area |
| `asset_type` | Controlled string | SCADA server, PLC, RTU, workstation, historian, gateway, network device or other class |
| `manufacturer` | Optional string | OEM or supplier |
| `model` | Optional string | Product family or model |
| `software_version` | Optional string | Application or runtime version |
| `firmware_version` | Optional string | Firmware version where relevant |
| `os_version` | Optional string | Operating-system generation or build |
| `support_status` | `supported`, `limited`, `end_of_support`, `unknown` | Current lifecycle state used by the risk model |
| `support_end_date` | ISO date `YYYY-MM-DD` | Evidence-backed support or service end date |
| `business_criticality` | Integer 1–5 | Overall business consequence |
| `safety_impact` | Integer 1–5 | Potential personnel or process-safety consequence |
| `production_impact` | Integer 1–5 | Service, output or availability consequence |
| `cyber_exposure` | Integer 1–5 | Exposure created by access, architecture and security limitations |
| `failure_likelihood` | Integer 1–5 | Likelihood of disruptive failure based on age, condition and history |
| `spares_risk` | Integer 1–5 | Scarcity, repairability and lead-time exposure |
| `recoverability_risk` | Integer 1–5 | Weakness of backups, restore evidence, redundancy or recovery time |
| `dependency_complexity` | Integer 1–5 | Complexity of interfaces, downstream consumers and migration coupling |
| `evidence_confidence` | `A`, `B`, `C`, `D` | A: authoritative; B: verified; C: inferred; D: unknown |
| `delivery_readiness` | Integer 1–5 | 1: discovery required; 5: ready to execute |
| `treatment` | Controlled string | Assess, retain, contain, upgrade, replace, redesign or decommission |
| `owner` | Optional string | Accountable operational or technical owner |
| `notes` | Optional text | Evidence gaps, dependencies, constraints and immediate controls |
| `programme_id` | Optional foreign key | Link to a programme package through the API |
| `programme_code` | Optional CSV field | Human-friendly package link used during import and export |

## Computed asset fields

These fields are owned by the backend and are recalculated whenever an assessment changes. Imported values are ignored.

| Field | Rule |
|---|---|
| `risk_score` | Weighted 0–100 score plus evidence-confidence penalty |
| `risk_band` | Low, Medium, High or Critical |
| `recommended_wave` | Wave 0, Wave 1, Wave 2 or Monitor |
| `data_completeness` | Percentage of key identity, lifecycle and accountability fields populated |
| `created_at` | Database creation timestamp |
| `updated_at` | Most recent database update timestamp |

## Programme package

| Field | Type / rule | Purpose |
|---|---|---|
| `package_code` | Required unique string, max 50 | Persistent intervention-package identifier |
| `title` | Required string, max 200 | Programme work-package title |
| `description` | Optional text | Problem statement and intended outcome |
| `owner` | Optional string | Accountable delivery owner |
| `sponsor` | Optional string | Executive or operational sponsor |
| `status` | Controlled string | Discovery, options, business case, design, ready, delivery, acceptance or closed |
| `target_wave` | Controlled string | Wave 0, Wave 1, Wave 2, Wave 3, Monitor or Unassigned |
| `budget_estimate` | Non-negative decimal | Base cost estimate |
| `contingency_percent` | 0–100 | Estimate contingency |
| `target_start` | Optional ISO date | Planned start |
| `target_finish` | Optional ISO date | Planned completion |
| `outage_window` | Optional string | Operational shutdown or migration constraint |
| `target_platform` | Optional text | Target architecture, platform or service state |
| `dependencies` | Optional text | Technical, commercial, outage and project dependencies |
| `notes` | Optional text | Additional programme information |

The API derives `asset_count`, `critical_assets`, `average_risk` and `total_budget` from live linked records.

## Import behavior

- New rows require `asset_code`, `system_name` and `site`.
- The TPCMS live obsolescence-register format is also recognised and mapped before
  validation. See `docs/LIVE_REGISTER_MAPPING.md`.
- Existing records are matched by exact `asset_code` and updated.
- Empty optional CSV cells do not overwrite existing values.
- `programme_code` must already exist in the programme table.
- Ratings outside 1–5 are rejected for that row.
- A failed row is isolated by a database savepoint; valid rows remain importable.
- At most 25 detailed row errors are returned in one response.
