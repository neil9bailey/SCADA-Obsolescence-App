from __future__ import annotations

from collections import defaultdict
import csv
import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Asset, Programme
from app.schemas import AssetCreate, AssetListResponse, AssetRead, AssetUpdate, ImportResult, Message
from app.services.audit import log_event
from app.services.live_register_import import (
    is_live_register_fieldnames,
    live_register_natural_key,
    map_live_register_row,
    read_live_register_workbook,
)
from app.services.risk import apply_assessment

router = APIRouter(prefix="/assets", tags=["assets"])

SORT_FIELDS = {
    "asset_code": Asset.asset_code,
    "system_name": Asset.system_name,
    "site": Asset.site,
    "risk_score": Asset.risk_score,
    "risk_band": Asset.risk_band,
    "support_status": Asset.support_status,
    "updated_at": Asset.updated_at,
}

CSV_FIELDS = [
    "asset_code",
    "system_name",
    "site",
    "process_area",
    "asset_type",
    "manufacturer",
    "model",
    "software_version",
    "firmware_version",
    "os_version",
    "support_status",
    "support_end_date",
    "business_criticality",
    "safety_impact",
    "production_impact",
    "cyber_exposure",
    "failure_likelihood",
    "spares_risk",
    "recoverability_risk",
    "dependency_complexity",
    "evidence_confidence",
    "delivery_readiness",
    "treatment",
    "owner",
    "notes",
    "programme_code",
    "risk_score",
    "risk_band",
    "recommended_wave",
    "data_completeness",
]

SOURCE_EXPORT_PLATFORM_FIELDS = [
    "platform_asset_code",
    "platform_risk_score",
    "platform_risk_band",
    "platform_recommended_wave",
    "platform_support_status",
    "platform_treatment",
    "platform_evidence_confidence",
    "platform_data_completeness",
    "platform_source_workbook",
    "platform_source_sheet",
    "platform_source_row",
    "platform_source_category",
    "platform_source_subcategory",
    "platform_automation_flags",
    "platform_formula_columns",
]

INTEGER_FIELDS = {
    "business_criticality",
    "safety_impact",
    "production_impact",
    "cyber_exposure",
    "failure_likelihood",
    "spares_risk",
    "recoverability_risk",
    "dependency_complexity",
    "delivery_readiness",
    "programme_id",
}

SOURCE_FIELDS = {
    "source_workbook",
    "source_sheet",
    "source_row",
    "source_category",
    "source_subcategory",
    "source_payload",
    "source_formulas",
    "source_intelligence",
}


def _get_asset_or_404(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


def _programme_exists(db: Session, programme_id: int | None) -> bool:
    return programme_id is None or db.get(Programme, programme_id) is not None


def _normalise_csv_row(
    raw: dict[str, Any],
    *,
    line_number: int,
    duplicate_index: int = 1,
    source_workbook: str | None = None,
    source_sheet: str | None = None,
    source_row: int | None = None,
    source_payload: dict[str, Any] | None = None,
    source_formulas: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in raw.items():
        if key is None:
            continue
        clean_key = key.strip().lstrip("\ufeff")
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            value = None
        row[clean_key] = value

    if "asset_code" not in row and is_live_register_fieldnames(list(row)):
        row = map_live_register_row(
            row,
            line_number=line_number,
            duplicate_index=duplicate_index,
            source_workbook=source_workbook,
            source_sheet=source_sheet,
            source_row=source_row,
            source_payload=source_payload,
            source_formulas=source_formulas,
        )

    for field in INTEGER_FIELDS:
        if row.get(field) is not None:
            row[field] = int(row[field])
    return row


@router.get("/facets")
def get_facets(db: Session = Depends(get_db)) -> dict:
    sites = db.scalars(select(Asset.site).distinct().order_by(Asset.site)).all()
    asset_types = db.scalars(select(Asset.asset_type).distinct().order_by(Asset.asset_type)).all()
    source_categories = db.scalars(select(Asset.source_category).distinct().order_by(Asset.source_category)).all()
    source_subcategories = db.scalars(
        select(Asset.source_subcategory).distinct().order_by(Asset.source_subcategory)
    ).all()
    programmes = db.scalars(select(Programme).order_by(Programme.package_code)).all()
    return {
        "sites": [site for site in sites if site],
        "asset_types": [value for value in asset_types if value],
        "source_categories": [value for value in source_categories if value],
        "source_subcategories": [value for value in source_subcategories if value],
        "programmes": [
            {"id": programme.id, "package_code": programme.package_code, "title": programme.title}
            for programme in programmes
        ],
        "support_statuses": ["supported", "limited", "end_of_support", "unknown"],
        "risk_bands": ["Critical", "High", "Medium", "Low"],
        "treatments": ["assess", "retain", "contain", "upgrade", "replace", "redesign", "decommission"],
    }


@router.get("/export.csv")
def export_assets(db: Session = Depends(get_db)) -> StreamingResponse:
    assets = db.scalars(select(Asset).order_by(Asset.site, Asset.asset_code)).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for asset in assets:
        writer.writerow(
            {
                **{field: getattr(asset, field, "") for field in CSV_FIELDS if field != "programme_code"},
                "programme_code": asset.programme.package_code if asset.programme else "",
                "support_end_date": asset.support_end_date.isoformat() if asset.support_end_date else "",
            }
        )
    output.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="scada-obsolescence-register.csv"'}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/source-export.csv")
def export_source_assets(db: Session = Depends(get_db)) -> StreamingResponse:
    assets = db.scalars(select(Asset).order_by(Asset.source_row, Asset.asset_code)).all()
    source_assets = [asset for asset in assets if asset.source_payload]
    source_fields: list[str] = []
    seen_source_fields: set[str] = set()
    for asset in source_assets:
        for field in (asset.source_payload or {}):
            if field not in seen_source_fields:
                seen_source_fields.add(field)
                source_fields.append(field)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[*SOURCE_EXPORT_PLATFORM_FIELDS, *source_fields])
    writer.writeheader()
    for asset in source_assets:
        intelligence = asset.source_intelligence or {}
        row = {
            "platform_asset_code": asset.asset_code,
            "platform_risk_score": asset.risk_score,
            "platform_risk_band": asset.risk_band,
            "platform_recommended_wave": asset.recommended_wave,
            "platform_support_status": asset.support_status,
            "platform_treatment": asset.treatment,
            "platform_evidence_confidence": asset.evidence_confidence,
            "platform_data_completeness": asset.data_completeness,
            "platform_source_workbook": asset.source_workbook or "",
            "platform_source_sheet": asset.source_sheet or "",
            "platform_source_row": asset.source_row or "",
            "platform_source_category": asset.source_category or "",
            "platform_source_subcategory": asset.source_subcategory or "",
            "platform_automation_flags": ";".join(intelligence.get("automation_flags") or []),
            "platform_formula_columns": ";".join((asset.source_formulas or {}).keys()),
        }
        row.update(asset.source_payload or {})
        writer.writerow(row)

    output.seek(0)
    headers = {"Content-Disposition": 'attachment; filename="tpcms-source-register-export.csv"'}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.post("/import", response_model=ImportResult)
async def import_assets(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ImportResult:
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Upload a CSV file or recognised TPCMS workbook")

    contents = await file.read()
    filename = file.filename
    filename_lower = filename.lower()
    import_kind = "workbook" if filename_lower.endswith(".xlsx") else "CSV"

    if filename_lower.endswith(".xlsx"):
        try:
            import_rows = read_live_register_workbook(contents, filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        live_register = True
    else:
        try:
            text = contents.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

        reader = csv.DictReader(io.StringIO(text))
        fieldnames = [name.strip().lstrip("\ufeff") for name in reader.fieldnames or []]
        live_register = is_live_register_fieldnames(fieldnames)
        if not fieldnames or ("asset_code" not in fieldnames and not live_register):
            raise HTTPException(
                status_code=400,
                detail="CSV must contain an asset_code column or recognised live obsolescence register columns",
            )
        import_rows = [
            {
                "row": raw,
                "line_number": line_number,
                "source_workbook": filename if live_register else None,
                "source_sheet": "CSV" if live_register else None,
                "source_row": line_number if live_register else None,
                "source_payload": None,
                "source_formulas": None,
            }
            for line_number, raw in enumerate(reader, start=2)
        ]

    created = updated = failed = rows_received = 0
    errors: list[str] = []
    create_fields = set(AssetCreate.model_fields)
    update_fields = set(AssetUpdate.model_fields)
    duplicate_indexes: defaultdict[tuple[str, ...], int] = defaultdict(int)

    for import_row in import_rows:
        rows_received += 1
        line_number = int(import_row["line_number"])
        raw = import_row["row"]
        try:
            with db.begin_nested():
                duplicate_index = 1
                if live_register:
                    cleaned_raw = {key.strip().lstrip("\ufeff"): value for key, value in raw.items() if key is not None}
                    natural_key = live_register_natural_key(cleaned_raw)
                    duplicate_indexes[natural_key] += 1
                    duplicate_index = duplicate_indexes[natural_key]

                row = _normalise_csv_row(
                    raw,
                    line_number=line_number,
                    duplicate_index=duplicate_index,
                    source_workbook=import_row.get("source_workbook"),
                    source_sheet=import_row.get("source_sheet"),
                    source_row=import_row.get("source_row"),
                    source_payload=import_row.get("source_payload"),
                    source_formulas=import_row.get("source_formulas"),
                )
                source_updates = {field: row.pop(field) for field in SOURCE_FIELDS if field in row}
                programme_code = row.pop("programme_code", None)
                programme_id = row.get("programme_id")
                if programme_code:
                    programme = db.scalar(select(Programme).where(Programme.package_code == programme_code))
                    if not programme:
                        raise ValueError(f"unknown programme_code '{programme_code}'")
                    programme_id = programme.id
                    row["programme_id"] = programme_id

                asset_code = row.get("asset_code")
                if not asset_code:
                    raise ValueError("asset_code is required")
                existing = db.scalar(select(Asset).where(Asset.asset_code == str(asset_code)))

                if existing:
                    update_payload = {key: value for key, value in row.items() if key in update_fields and value is not None}
                    if programme_code is not None:
                        update_payload["programme_id"] = programme_id
                    validated = AssetUpdate.model_validate(update_payload)
                    if not _programme_exists(db, validated.programme_id):
                        raise ValueError("programme_id does not exist")
                    for key, value in validated.model_dump(exclude_unset=True).items():
                        setattr(existing, key, value)
                    for key, value in source_updates.items():
                        setattr(existing, key, value)
                    apply_assessment(existing)
                    db.flush()
                    updated += 1
                else:
                    create_payload = {key: value for key, value in row.items() if key in create_fields}
                    validated = AssetCreate.model_validate(create_payload)
                    if not _programme_exists(db, validated.programme_id):
                        raise ValueError("programme_id does not exist")
                    asset = Asset(**validated.model_dump(), **source_updates)
                    apply_assessment(asset)
                    db.add(asset)
                    db.flush()
                    created += 1
        except (ValidationError, ValueError, TypeError, IntegrityError) as exc:
            failed += 1
            message = str(exc).replace("\n", " ")
            errors.append(f"Row {line_number}: {message[:220]}")
            if len(errors) >= 25:
                errors.append("Further errors omitted")
                break

    log_event(
        db,
        entity_type="asset",
        entity_id=None,
        action="import",
        summary=f"Imported {import_kind}: {created} created, {updated} updated, {failed} failed",
    )
    db.commit()
    return ImportResult(
        rows_received=rows_received,
        created=created,
        updated=updated,
        failed=failed,
        errors=errors,
    )


@router.get("", response_model=AssetListResponse)
def list_assets(
    q: str | None = None,
    site: str | None = None,
    asset_type: str | None = None,
    support_status: str | None = None,
    risk_band: str | None = None,
    programme_id: int | None = None,
    source_category: str | None = None,
    source_subcategory: str | None = None,
    sort_by: str = Query(default="risk_score"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=250),
    db: Session = Depends(get_db),
) -> AssetListResponse:
    filters = []
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                Asset.asset_code.ilike(pattern),
                Asset.system_name.ilike(pattern),
                Asset.manufacturer.ilike(pattern),
                Asset.model.ilike(pattern),
                Asset.owner.ilike(pattern),
            )
        )
    if site:
        filters.append(Asset.site == site)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if support_status:
        filters.append(Asset.support_status == support_status)
    if risk_band:
        filters.append(Asset.risk_band == risk_band)
    if programme_id is not None:
        filters.append(Asset.programme_id == programme_id)
    if source_category:
        filters.append(Asset.source_category == source_category)
    if source_subcategory:
        filters.append(Asset.source_subcategory == source_subcategory)

    count_statement = select(func.count()).select_from(Asset)
    statement = select(Asset)
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)

    sort_column = SORT_FIELDS.get(sort_by, Asset.risk_score)
    ordering = desc(sort_column) if sort_dir == "desc" else asc(sort_column)
    statement = statement.order_by(ordering, Asset.asset_code).offset(offset).limit(limit)

    total = int(db.scalar(count_statement) or 0)
    items = list(db.scalars(statement).all())
    return AssetListResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)) -> Asset:
    if db.scalar(select(Asset).where(Asset.asset_code == payload.asset_code)):
        raise HTTPException(status_code=409, detail="asset_code already exists")
    if not _programme_exists(db, payload.programme_id):
        raise HTTPException(status_code=400, detail="programme_id does not exist")

    asset = Asset(**payload.model_dump())
    apply_assessment(asset)
    db.add(asset)
    db.flush()
    log_event(
        db,
        entity_type="asset",
        entity_id=asset.id,
        action="create",
        summary=f"Created {asset.asset_code} · {asset.system_name}",
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, db: Session = Depends(get_db)) -> Asset:
    return _get_asset_or_404(db, asset_id)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db)) -> Asset:
    asset = _get_asset_or_404(db, asset_id)
    updates = payload.model_dump(exclude_unset=True)

    if "asset_code" in updates and updates["asset_code"] != asset.asset_code:
        duplicate = db.scalar(select(Asset).where(Asset.asset_code == updates["asset_code"]))
        if duplicate:
            raise HTTPException(status_code=409, detail="asset_code already exists")
    if "programme_id" in updates and not _programme_exists(db, updates["programme_id"]):
        raise HTTPException(status_code=400, detail="programme_id does not exist")

    for key, value in updates.items():
        setattr(asset, key, value)
    apply_assessment(asset)
    log_event(
        db,
        entity_type="asset",
        entity_id=asset.id,
        action="update",
        summary=f"Updated {asset.asset_code} · risk {asset.risk_band} {asset.risk_score}",
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", response_model=Message)
def delete_asset(asset_id: int, db: Session = Depends(get_db)) -> Message:
    asset = _get_asset_or_404(db, asset_id)
    summary = f"Deleted {asset.asset_code} · {asset.system_name}"
    log_event(db, entity_type="asset", entity_id=asset.id, action="delete", summary=summary)
    db.delete(asset)
    db.commit()
    return Message(message=summary)
