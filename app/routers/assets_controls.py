from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Asset, merge_source_payload
from app.schemas import AssetListResponse, AssetRead
from app.schemas_live import AssetSourceFieldsRead, AssetSourceFieldsUpdate, AssetVisibilityUpdate
from app.services.source_payloads import sync_source_payload
from app.services.audit import log_event
from app.services.source_columns import SOURCE_REGISTER_COLUMNS, blank_source_payload, source_column_definitions

router = APIRouter(prefix="/assets", tags=["assets"])
SORT_FIELDS = {"asset_code": Asset.asset_code, "system_name": Asset.system_name, "site": Asset.site, "risk_score": Asset.risk_score, "risk_band": Asset.risk_band, "support_status": Asset.support_status, "updated_at": Asset.updated_at, "visibility_status": Asset.visibility_status, "evidence_status": Asset.evidence_status}


def _asset(db, asset_id:int):
    asset=db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.get("/source-columns")
def source_columns():
    return [column.model_dump() for column in source_column_definitions()]

@router.get("", response_model=AssetListResponse)
def list_assets(q:str|None=None, site:str|None=None, asset_type:str|None=None, support_status:str|None=None, risk_band:str|None=None, programme_id:int|None=None, source_category:str|None=None, source_subcategory:str|None=None, visibility_status:str|None=None, evidence_status:str|None=None, include_retained:bool=False, sort_by:str=Query(default="risk_score"), sort_dir:str=Query(default="desc", pattern="^(asc|desc)$"), offset:int=Query(default=0, ge=0), limit:int=Query(default=25, ge=1, le=250), db:Session=Depends(get_db)):
    filters=[]
    if q:
        pattern=f"%{q.strip()}%"
        filters.append(or_(Asset.asset_code.ilike(pattern),Asset.system_name.ilike(pattern),Asset.manufacturer.ilike(pattern),Asset.model.ilike(pattern),Asset.owner.ilike(pattern)))
    for value,column in ((site,Asset.site),(asset_type,Asset.asset_type),(support_status,Asset.support_status),(risk_band,Asset.risk_band),(programme_id,Asset.programme_id),(source_category,Asset.source_category),(source_subcategory,Asset.source_subcategory),(visibility_status,Asset.visibility_status),(evidence_status,Asset.evidence_status)):
        if value not in (None,""):
            filters.append(column==value)
    if not include_retained and not visibility_status:
        filters.append(Asset.is_active.is_(True))
    count=select(func.count()).select_from(Asset)
    statement=select(Asset)
    if filters:
        count=count.where(*filters); statement=statement.where(*filters)
    sort_column=SORT_FIELDS.get(sort_by,Asset.risk_score)
    statement=statement.order_by(desc(sort_column) if sort_dir=="desc" else asc(sort_column), Asset.asset_code).offset(offset).limit(limit)
    return AssetListResponse(items=list(db.scalars(statement).all()), total=int(db.scalar(count) or 0), offset=offset, limit=limit)

@router.get("/{asset_id}/source-fields", response_model=AssetSourceFieldsRead)
def get_source_fields(asset_id:int, db:Session=Depends(get_db)):
    asset=_asset(db, asset_id)
    original=asset.source_payload_original or asset.source_payload or blank_source_payload()
    overrides=asset.source_payload_overrides or {}
    effective=merge_source_payload(original, overrides) or {}
    return AssetSourceFieldsRead(asset_id=asset.id, source_record_state=asset.source_record_state, source_workbook=asset.source_workbook, source_sheet=asset.source_sheet, source_row=asset.source_row, columns=source_column_definitions(), original=original, overrides=overrides, effective=effective, formulas=asset.source_formulas or {})

@router.patch("/{asset_id}/source-fields", response_model=AssetRead)
def update_source_fields(asset_id:int, payload:AssetSourceFieldsUpdate, db:Session=Depends(get_db)):
    asset=_asset(db, asset_id)
    original=asset.source_payload_original or asset.source_payload or blank_source_payload()
    overrides=dict(asset.source_payload_overrides or {})
    for key,value in payload.fields.items():
        if key not in SOURCE_REGISTER_COLUMNS:
            raise HTTPException(status_code=400, detail=f"unknown source field '{key}'")
        overrides[key]=value
    asset.source_payload_original=original
    asset.source_payload_overrides=overrides
    sync_source_payload(asset)
    log_event(db, entity_type="asset", entity_id=asset.id, action="source_update", summary=f"Updated {len(payload.fields)} source fields for {asset.asset_code}")
    db.commit(); db.refresh(asset)
    return asset

@router.patch("/{asset_id}/visibility", response_model=AssetRead)
def update_visibility(asset_id:int, payload:AssetVisibilityUpdate, db:Session=Depends(get_db)):
    asset=_asset(db, asset_id)
    asset.visibility_status=payload.visibility_status
    asset.is_active=payload.visibility_status=="active"
    asset.visibility_reason=payload.visibility_reason
    log_event(db, entity_type="asset", entity_id=asset.id, action="visibility", summary=f"Set {asset.asset_code} visibility to {asset.visibility_status}")
    db.commit(); db.refresh(asset)
    return asset
