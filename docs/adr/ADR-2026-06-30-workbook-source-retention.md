# ADR-2026-06-30: Preserve TPCMS Workbook Source Rows as Structured Asset Metadata

Status: Approved

Date: 2026-06-30

## Context

The authoritative TPCMS obsolescence source is the full Excel workbook:

```text
data/442075 TPCMS Obsolescence Register LIVE.xlsx
```

The workbook contains the visible register, a front sheet, a risk-factor key, and a hidden
PA certificate cross-reference sheet. The `Obsolescence Register` sheet contains 344 data
rows and 43 columns. Several register columns are formula-derived, including cost hit date,
total component/labour cost, criticality rating, source risk score, source risk factor, and
reason for risk.

The existing platform model normalizes each imported row into an `Asset` and preserves extra
source context in `notes`. That is acceptable for basic import, but it is not sufficient for
the workbook-source requirement because the source columns must remain available as-is for
automation, filtering, reporting, audit, and future refreshes.

## Decision

Preserve workbook source rows as structured metadata attached to each normalized asset.

The `assets` table will be extended with source-retention fields:

- source workbook name
- source sheet name
- source row number
- source payload containing all original workbook columns and cached formula values
- source formula payload for workbook formulas
- source intelligence payload for derived grouping and data-quality signals
- source category and subcategory values for high-value filtering

The normalized fields remain the operational model used by dashboards, CRUD, programmes and
platform risk scoring. Source payloads are retained alongside the normalized asset record so
the app can report in the customer's familiar workbook language without giving up the
platform model.

The importer will support both:

- platform-native CSV files
- the TPCMS workbook `.xlsx`

For `.xlsx`, ingestion reads the `Obsolescence Register` sheet, keeps source formula cached
values, stores formulas separately, maps the row into normalized fields, and upserts by the
same stable generated asset code strategy.

## Consequences

Positive:

- Customers can continue mapping against their existing workbook fields.
- Source columns and formula-derived workbook intelligence remain available after import.
- The platform can automate refreshes and compare future workbook versions without requiring
  users to manually convert to CSV.
- Reporting can group by source categories such as responsible team, area, hardware/software,
  source status, source risk factor, replacement state and support evidence.

Trade-offs:

- The asset model gains source-retention fields and requires an Alembic migration.
- Source payload filtering is best kept to bounded datasets or promoted indexed fields; it is
  not a replacement for a large analytic warehouse.
- Workbook formulas are preserved as source evidence, but the platform still owns its own
  normalized risk score and delivery-wave recommendation.

## Constraints

- Do not mutate the supplied workbook during ingestion.
- Do not auto-create programme packages from `Area`, `Responsible Team`, or another source
  taxonomy without a human-approved packaging rule.
- Keep import row isolation: a bad row must not discard valid workbook rows.
- Keep the existing browser-to-FastAPI-to-SQLAlchemy architecture.

## Verification

Implementation must verify:

- API tests pass.
- Alembic upgrade/check passes.
- The supplied workbook imports cleanly into an empty database with demo seeding disabled.
- Re-importing the same workbook updates existing records instead of duplicating them.
- Dashboard, asset register, data exchange and source-reporting views/API paths work against
  the imported data.
- The original workbook file remains unmodified.
