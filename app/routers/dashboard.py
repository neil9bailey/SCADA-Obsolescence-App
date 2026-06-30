from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Asset, AuditEvent, Programme

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _top_counts(counter: Counter, limit: int = 12) -> list[dict]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    assets = list(db.scalars(select(Asset).order_by(desc(Asset.risk_score))).all())
    programmes = list(db.scalars(select(Programme).options(selectinload(Programme.assets))).all())
    recent = list(db.scalars(select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(8)).all())

    risk_counts = Counter(asset.risk_band for asset in assets)
    support_counts = Counter(asset.support_status for asset in assets)
    programme_status_counts = Counter(programme.status for programme in programmes)
    wave_counts = Counter(asset.recommended_wave for asset in assets)

    site_data: dict[str, list[Asset]] = defaultdict(list)
    for asset in assets:
        site_data[asset.site].append(asset)

    sites = []
    for site, site_assets in site_data.items():
        sites.append(
            {
                "site": site,
                "assets": len(site_assets),
                "high_risk": sum(1 for asset in site_assets if asset.risk_band in {"Critical", "High"}),
                "average_risk": round(sum(asset.risk_score for asset in site_assets) / len(site_assets), 1),
            }
        )
    sites.sort(key=lambda item: (item["average_risk"], item["high_risk"]), reverse=True)

    total_budget = sum(
        float(programme.budget_estimate or Decimal("0")) * (1 + programme.contingency_percent / 100)
        for programme in programmes
    )
    average_risk = round(sum(asset.risk_score for asset in assets) / len(assets), 1) if assets else 0
    average_completeness = (
        round(sum(asset.data_completeness for asset in assets) / len(assets)) if assets else 0
    )

    return {
        "generated_from": "live_database",
        "metrics": {
            "total_assets": len(assets),
            "high_risk_assets": sum(1 for asset in assets if asset.risk_band in {"Critical", "High"}),
            "unsupported_assets": support_counts.get("end_of_support", 0),
            "unknown_lifecycle": support_counts.get("unknown", 0),
            "average_risk": average_risk,
            "active_programmes": sum(1 for programme in programmes if programme.status != "closed"),
            "funding_estimate": round(total_budget, 2),
            "data_completeness": average_completeness,
        },
        "risk_bands": [
            {"name": name, "count": risk_counts.get(name, 0)}
            for name in ("Critical", "High", "Medium", "Low")
        ],
        "support_status": [
            {"name": name, "count": support_counts.get(name, 0)}
            for name in ("end_of_support", "limited", "unknown", "supported")
        ],
        "programme_status": [
            {"name": name, "count": count} for name, count in sorted(programme_status_counts.items())
        ],
        "waves": [
            {"name": name, "count": wave_counts.get(name, 0)}
            for name in ("Wave 0", "Wave 1", "Wave 2", "Monitor")
        ],
        "sites": sites[:10],
        "top_assets": [
            {
                "id": asset.id,
                "asset_code": asset.asset_code,
                "system_name": asset.system_name,
                "site": asset.site,
                "risk_score": asset.risk_score,
                "risk_band": asset.risk_band,
                "support_status": asset.support_status,
                "recommended_wave": asset.recommended_wave,
            }
            for asset in assets[:8]
        ],
        "data_quality": {
            "average_completeness": average_completeness,
            "low_confidence": sum(1 for asset in assets if asset.evidence_confidence in {"C", "D"}),
            "missing_owner": sum(1 for asset in assets if not asset.owner),
            "missing_support_date": sum(1 for asset in assets if not asset.support_end_date),
            "unassigned_programme": sum(1 for asset in assets if not asset.programme_id),
        },
        "recent_activity": [
            {
                "id": event.id,
                "entity_type": event.entity_type,
                "action": event.action,
                "summary": event.summary,
                "actor": event.actor,
                "created_at": event.created_at,
            }
            for event in recent
        ],
    }


@router.get("/source-summary")
def source_summary(db: Session = Depends(get_db)) -> dict:
    assets = list(db.scalars(select(Asset)).all())
    source_assets = [asset for asset in assets if asset.source_payload]
    source_categories = Counter(asset.source_category for asset in source_assets if asset.source_category)
    source_subcategories = Counter(asset.source_subcategory for asset in source_assets if asset.source_subcategory)
    source_risk_factors: Counter = Counter()
    source_statuses: Counter = Counter()
    hardware_software: Counter = Counter()
    automation_flags: Counter = Counter()
    formula_columns: Counter = Counter()
    total_estimated_cost = 0.0
    total_quantity_in_field = 0

    for asset in source_assets:
        intelligence = asset.source_intelligence or {}
        payload = asset.source_payload or {}
        collation = intelligence.get("collation") or {}
        if intelligence.get("source_risk_factor"):
            source_risk_factors[intelligence["source_risk_factor"]] += 1
        if intelligence.get("source_status"):
            source_statuses[intelligence["source_status"]] += 1
        if collation.get("hardware_software"):
            hardware_software[collation["hardware_software"]] += 1
        for flag in intelligence.get("automation_flags") or []:
            automation_flags[flag] += 1
        for column in (asset.source_formulas or {}):
            formula_columns[column] += 1
        if isinstance(intelligence.get("source_total_estimated_cost"), (int, float)):
            total_estimated_cost += float(intelligence["source_total_estimated_cost"])
        if isinstance(intelligence.get("source_quantity_in_field"), int):
            total_quantity_in_field += int(intelligence["source_quantity_in_field"])
        elif isinstance(payload.get("Qty in Field"), int):
            total_quantity_in_field += int(payload["Qty in Field"])

    return {
        "generated_from": "source_workbook_metadata",
        "source_records": len(source_assets),
        "source_workbooks": sorted({asset.source_workbook for asset in source_assets if asset.source_workbook}),
        "source_sheets": sorted({asset.source_sheet for asset in source_assets if asset.source_sheet}),
        "totals": {
            "estimated_cost": round(total_estimated_cost, 2),
            "quantity_in_field": total_quantity_in_field,
            "formula_columns": len(formula_columns),
        },
        "source_categories": _top_counts(source_categories),
        "source_subcategories": _top_counts(source_subcategories),
        "source_risk_factors": _top_counts(source_risk_factors),
        "source_statuses": _top_counts(source_statuses),
        "hardware_software": _top_counts(hardware_software),
        "automation_flags": _top_counts(automation_flags),
        "formula_columns": _top_counts(formula_columns),
    }
