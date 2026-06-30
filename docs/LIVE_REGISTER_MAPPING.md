# Live TPCMS register mapping

This note records how the supplied live file is mapped into the SCADA Lifecycle Command
Centre:

```text
data/442075 TPCMS Obsolescence Register LIVE Obsolescence Register.csv
```

## Source profile

The live register is a UTF-8 CSV with a byte-order mark. It contains 344 data rows and 43
columns. It does not contain the platform-native `asset_code`, `system_name` or `site`
columns, so the importer recognises this source shape and maps it before validation.

The final source column is blank and is ignored.

## Identity and upsert key

The platform still upserts by `asset_code`. For live-register rows, the importer generates a
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
hash input so both rows remain distinct. Re-importing the same file updates the same 344
records instead of creating duplicates.

## Field mapping

| Live register column | Platform field | Notes |
|---|---|---|
| `Component Part` | `model`, generated `asset_code` | Preserved in notes as well |
| `Component` | `system_name`, `asset_type` | Falls back to description or part where blank |
| `Component Description` | `notes` | Also used as identity-hash input |
| `Manufacturer` | `manufacturer` | Falls back to `Supplier` when needed |
| `Supplier` | `notes` | Used only as manufacturer fallback when manufacturer is blank |
| `Responsible Team` | `process_area`, `owner` | Blank values remain visible as missing-owner quality gaps |
| `Area` | `site` | Falls back to `TPCMS` when blank |
| `Hardware/Software` | risk inference, notes | Software/network rows receive higher cyber-exposure defaults |
| `Functional / Non-Functional` | `safety_impact` inference | Functional rows retain system criticality; non-functional rows reduce it by one |
| `Obsolete (Y/N)` | `support_status`, `treatment` | Obsolete rows without a usable date are treated as end-of-support |
| `End of Support` | `support_end_date`, `support_status` | `DD-MMM-YY`, ISO and UK slash dates are parsed |
| `Status` | `treatment`, `delivery_readiness`, notes | Decommissioned/no-component rows are treated as monitor/decommission candidates |
| `System Criticality` | `business_criticality`, `production_impact`, `dependency_complexity` | Non-numeric values fall back to source risk factor or default 3 |
| `Obsolescence Criticality` | `failure_likelihood`, `recoverability_risk`, `dependency_complexity` | Non-numeric values fall back to source risk factor or default 3 |
| `Cost Criticality` | `recoverability_risk` | Preserved in notes because there is no dedicated cost-risk field |
| Spares quantity columns | `spares_risk` | Recommended spares are compared with battle-box plus Telent spares |
| `Replacement identified (Y/N)` | `treatment`, `delivery_readiness` | Replacement identified increases readiness |
| `Full upgrade or ad-hoc replacement?` | `treatment` | Full upgrade maps to replace; ad-hoc maps to upgrade |
| `Risk Score`, `Risk Factor`, `Reason for Risk`, `Risk Assessment` | `notes` | Source risk is preserved; platform risk is recalculated from mapped inputs |
| Cost, certificate, lead-time, strategy and supporting-note fields | `notes` | Retained as line-based evidence text |

## Programme packages

The supplied register does not include `programme_code` values or an approved delivery
package structure. The importer therefore leaves all imported rows unassigned. The
Programme packages view then correctly shows 344 unassigned assets, ready for a human-owned
packaging decision by area, treatment, delivery wave or another approved grouping.

Do not auto-create programme packages from `Area` or `Responsible Team` without an approved
delivery decision. That would turn a source taxonomy into a delivery commitment.

## Clean local import sequence

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
data/442075 TPCMS Obsolescence Register LIVE Obsolescence Register.csv
```

## Validation evidence

Validation on the supplied file:

- First clean import: 344 rows received, 344 created, 0 failed.
- Repeat import: 344 rows received, 0 created, 344 updated, 0 failed.
- Dashboard after import: 344 assets, 32 high or critical, 82 unsupported, 39 unknown
  lifecycle, 93 percent average completeness.
- Export after import: 344 asset rows.
