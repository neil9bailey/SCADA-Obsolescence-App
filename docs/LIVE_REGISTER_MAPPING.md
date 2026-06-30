# Live TPCMS Register Mapping

This note records how the supplied live workbook is imported into the SCADA Lifecycle
Command Centre:

```text
data/442075 TPCMS Obsolescence Register LIVE.xlsx
```

The earlier CSV export of this workbook remains supported as a legacy transfer shape, but
the workbook is now the authoritative source format for local import testing.

## Workbook Profile

The workbook contains four sheets:

| Sheet | Visibility | Use |
|---|---|---|
| `Front Sheet` | Visible | Human-facing workbook cover and notes |
| `Obsolescence Register` | Visible | Imported source register |
| `Risk Factor Key` | Visible | Source risk-scoring reference |
| `PA certs items cross-ref` | Hidden | Certificate cross-reference evidence |

The importer reads `Obsolescence Register`. The profiled workbook has 344 data rows, 43
register columns, freeze panes at `E324`, and an autofilter over `A1:AC324`.

Formula columns are preserved as formula evidence where present. In the supplied workbook
these include cost-hit date, total component/labour cost, criticality rating, replacement,
source risk score, source risk factor and source risk reason columns.

## Identity And Upsert Key

The workbook does not provide platform-native `asset_code` values. The importer generates a
stable code:

```text
TPCMS-<component-part-or-component-slug>-<8-character-hash>
```

The hash is based on:

- `Component Part`
- `Component`
- `Area`
- `Manufacturer`
- `Hardware/Software`
- `Component Description`

If the source has exact duplicate identities, the duplicate occurrence is included in the
hash input so both rows remain distinct. Re-importing the same workbook updates the same
344 records instead of creating duplicates.

## Source Retention

Every imported workbook row is stored in two forms:

- normalized asset fields used by the platform dashboards, CRUD screens, risk model and
  programme packages
- structured source metadata that preserves the customer-facing workbook language

Retained source metadata includes:

- `source_workbook`
- `source_sheet`
- `source_row`
- `source_category` from `Area`
- `source_subcategory` from `Responsible Team`
- `source_payload` with all original source columns and cached cell values
- `source_formulas` with workbook formula text
- `source_intelligence` with source risk, source status, collation values and automation
  flags

The source workbook is not mutated during import.

## Field Mapping

| Live register column | Platform field | Notes |
|---|---|---|
| `Component Part` | `model`, generated `asset_code` | Also retained in `source_payload` and notes |
| `Component` | `system_name`, `asset_type` | Falls back to description or part where blank |
| `Component Description` | `notes` | Also used as identity-hash input |
| `Manufacturer` | `manufacturer` | Falls back to `Supplier` when needed |
| `Supplier` | `notes` | Used only as manufacturer fallback when manufacturer is blank |
| `Responsible Team` | `process_area`, `owner`, `source_subcategory` | Blank values remain visible as missing-owner quality gaps |
| `Area` | `site`, `source_category` | Falls back to `TPCMS` when blank |
| `Hardware/Software` | source collation, risk inference, notes | Software/network rows receive higher cyber-exposure defaults |
| `Functional / Non-Functional` | `safety_impact` inference | Functional rows retain system criticality; non-functional rows reduce it by one |
| `Obsolete (Y/N)` | `support_status`, `treatment` | Obsolete rows without a usable date are treated as end-of-support |
| `End of Support` | `support_end_date`, `support_status` | Excel dates, `DD-MMM-YY`, ISO and UK slash dates are parsed |
| `Status` | `treatment`, `delivery_readiness`, source status | Decommissioned/no-component rows are treated as monitor/decommission candidates |
| `System Criticality` | `business_criticality`, `production_impact`, `dependency_complexity` | Non-numeric values fall back to source risk factor or default 3 |
| `Obsolescence Criticality` | `failure_likelihood`, `recoverability_risk`, `dependency_complexity` | Non-numeric values fall back to source risk factor or default 3 |
| `Cost Criticality` | `recoverability_risk` | Preserved as source evidence because there is no dedicated cost-risk field |
| Spares quantity columns | `spares_risk`, automation flags | Recommended spares are compared with battle-box plus Telent spares |
| `Replacement identified (Y/N)` | `treatment`, `delivery_readiness`, source intelligence | Replacement identified increases readiness |
| `Full upgrade or ad-hoc replacement?` | `treatment` | Full upgrade maps to replace; ad-hoc maps to upgrade |
| `Risk Score`, `Risk Factor`, `Reason for Risk`, `Risk Assessment` | `notes`, `source_intelligence` | Source risk is preserved; platform risk is recalculated from mapped inputs |
| Cost, certificate, lead-time, strategy and supporting-note fields | `notes`, `source_payload` | Retained as source evidence and available in source export |

## Intelligence And Reporting

The source-intelligence payload adds automation signals without changing the customer's
source data. Current signals include:

- source high risk
- end of support without confirmed replacement
- spares below recommended level
- missing owner
- missing support date
- no component in field
- missing source risk score

The dashboard source summary reports source workbook counts, area/team groupings, source
risk factors, source statuses, hardware/software groups, automation flags, formula columns,
source total estimate and quantity in field.

The asset register can filter by source area and source responsible team. The API exposes
the same filters as `source_category` and `source_subcategory`.

## Programme Packages

The supplied workbook does not include `programme_code` values or an approved delivery
package structure. The importer therefore leaves all imported rows unassigned.

Programme package creation remains a human-owned governance decision. Do not auto-create
programme packages from `Area`, `Responsible Team`, or another source taxonomy without an
approved packaging rule.

## Clean Local Import Sequence

Use this sequence for a clean local database:

```powershell
cd F:\code\SCADA-Obsolescence-App
$env:SEED_DEMO = "false"
$env:AUTO_CREATE_SCHEMA = "true"
if (Test-Path .\data\scada_obsolescence.db) {
  Remove-Item -LiteralPath .\data\scada_obsolescence.db -Force
}
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000`, go to Data exchange and import:

```text
data/442075 TPCMS Obsolescence Register LIVE.xlsx
```

API import is also supported:

```powershell
$form = @{
  file = Get-Item ".\data\442075 TPCMS Obsolescence Register LIVE.xlsx"
}

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/assets/import `
  -Form $form
```

## Export Routes

- `/api/assets/export.csv`: normalized platform register for round trip or offline review.
- `/api/assets/source-export.csv`: original workbook columns with platform-calculated risk,
  wave, source category, automation flags and formula-column evidence.

## Validation Evidence

Validation on the supplied workbook after a clean local import:

- First clean import: 344 rows received, 344 created, 0 failed.
- Repeat import: 344 rows received, 0 created, 344 updated, 0 failed.
- Dashboard after import: 344 assets, 32 high or critical, 83 unsupported, 39 unknown
  lifecycle, 93 percent average completeness.
- Source summary: 344 source records, workbook name retained, 9 formula columns retained,
  8,005 quantity in field, and 17,463,620.00 total source estimate.
- Source export: 344 rows, 57 columns, including original workbook columns and `platform_`
  fields.
- Normalized export: 344 rows, 30 columns.
- Workbook hash and modification timestamp were unchanged by import.
