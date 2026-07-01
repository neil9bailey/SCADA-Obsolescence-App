from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.db import get_db
from app.models import Asset, EvidenceRecord
from app.schemas import Message
from app.schemas_live import EvidenceConfirmRequest, EvidenceRecordRead
from app.services.audit import log_event
from app.services.risk import apply_assessment

router = APIRouter(prefix="/evidence", tags=["evidence"])


def _asset(db: Session, asset_id: int) -> Asset:
    asset = db.scalar(select(Asset).options(selectinload(Asset.evidence_records)).where(Asset.id == asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


def _record(db: Session, evidence_id: int) -> EvidenceRecord:
    item = db.get(EvidenceRecord, evidence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Evidence record not found")
    return item


def _hash(payload: dict[str, Any]) -> str:
    return sha256(repr(sorted(payload.items())).encode("utf-8")).hexdigest()


def _identity(asset: Asset) -> dict[str, Any]:
    source = asset.source_payload_effective or {}
    return {"asset_code": asset.asset_code, "vendor": asset.manufacturer or source.get("Manufacturer") or source.get("Supplier"), "model": asset.model or source.get("Component Part"), "component": asset.system_name or source.get("Component"), "software_version": asset.software_version, "firmware_version": asset.firmware_version, "os_version": asset.os_version}


def _candidate(asset: Asset, authority: str, evidence_type: str, source_name: str, source_url: str | None, confidence: float, notes: str) -> EvidenceRecord:
    identity = _identity(asset)
    return EvidenceRecord(asset_id=asset.id, evidence_type=evidence_type, authority=authority, source_name=source_name, source_url_or_endpoint=source_url, query_payload=identity, response_hash=_hash(identity), matched_vendor=identity.get("vendor"), matched_product=identity.get("model") or identity.get("component"), matched_version=identity.get("software_version") or identity.get("firmware_version") or identity.get("os_version"), confidence_score=confidence, evidence_status="candidate", notes=notes, raw_response={"candidate_only": True})


def _refresh(asset: Asset) -> None:
    confirmed = [item for item in asset.evidence_records if item.evidence_status == "confirmed"]
    candidates = [item for item in asset.evidence_records if item.evidence_status == "candidate"]
    asset.vendor_evidence_summary = {"total_records": len(asset.evidence_records), "confirmed": len(confirmed), "candidate": len(candidates), "authorities": sorted({item.authority for item in asset.evidence_records})}
    if confirmed:
        asset.evidence_status = "confirmed"
        asset.evidence_confidence = "A"
    elif candidates:
        asset.evidence_status = "candidate"


@router.post("/query/{asset_id}", response_model=list[EvidenceRecordRead])
def query_asset_evidence(asset_id: int, db: Session = Depends(get_db)) -> list[EvidenceRecord]:
    asset = _asset(db, asset_id)
    ident = _identity(asset)
    vendor = str(ident.get("vendor") or "").lower()
    model = str(ident.get("model") or "")
    version = " ".join(str(ident.get(k) or "") for k in ("component", "model", "software_version", "firmware_version", "os_version")).lower()
    records: list[EvidenceRecord] = []
    if "cisco" in vendor or model.upper().startswith(("WS-", "ISR", "CAT")):
        records.append(_candidate(asset, "Cisco", "vendor_lifecycle", "Cisco Support APIs - EoX", "https://developer.cisco.com/docs/support-apis/eox/", 65 if model else 35, "Official Cisco EoX candidate. Confirm exact product evidence before changing lifecycle status."))
    if ident.get("vendor") or model or ident.get("component"):
        records.append(_candidate(asset, "NIST NVD", "vulnerability_intelligence", "NVD CPE/CVE APIs", "https://nvd.nist.gov/developers", 50, "NVD provides CPE/CVE and KEV evidence, not vendor support lifecycle proof."))
    if "microsoft" in vendor or any(token in version for token in ("windows", "sql server", "server 2012", "server 2016", "server 2019", "server 2022")):
        records.append(_candidate(asset, "Microsoft", "vendor_lifecycle", "Microsoft Lifecycle", "https://learn.microsoft.com/lifecycle/", 60, "Microsoft lifecycle candidate. Confirm against official lifecycle evidence before updating status."))
    if not records:
        records.append(_candidate(asset, "Manual review", "manual_evidence_required", "Supplier notice required", None, 10, "No automatic vendor adapter matched this asset."))
    for record in records:
        db.add(record)
    db.flush(); db.refresh(asset); _refresh(asset); apply_assessment(asset)
    log_event(db, entity_type="asset", entity_id=asset.id, action="evidence_query", summary=f"Created {len(records)} evidence candidates for {asset.asset_code}")
    db.commit()
    return list(db.scalars(select(EvidenceRecord).where(EvidenceRecord.asset_id == asset_id).order_by(EvidenceRecord.created_at.desc())).all())

@router.get("/{asset_id}", response_model=list[EvidenceRecordRead])
def list_asset_evidence(asset_id: int, db: Session = Depends(get_db)) -> list[EvidenceRecord]:
    _asset(db, asset_id)
    return list(db.scalars(select(EvidenceRecord).where(EvidenceRecord.asset_id == asset_id).order_by(EvidenceRecord.created_at.desc())).all())

@router.post("/{evidence_id}/confirm", response_model=EvidenceRecordRead)
def confirm_evidence(evidence_id: int, payload: EvidenceConfirmRequest, db: Session = Depends(get_db)) -> EvidenceRecord:
    record = _record(db, evidence_id); asset = _asset(db, record.asset_id)
    record.evidence_status = "confirmed"; record.reviewed_by = payload.reviewer; record.reviewed_at = datetime.now(timezone.utc)
    if payload.support_status: asset.support_status = payload.support_status; record.lifecycle_status = payload.support_status
    if payload.support_end_date: asset.support_end_date = payload.support_end_date; record.support_end_date = payload.support_end_date
    if payload.notes: record.notes = f"{record.notes or ''}\nConfirmation notes: {payload.notes}".strip()
    _refresh(asset); apply_assessment(asset); log_event(db, entity_type="asset", entity_id=asset.id, action="evidence_confirm", summary=f"Confirmed evidence {record.id} for {asset.asset_code}")
    db.commit(); db.refresh(record); return record

@router.post("/{evidence_id}/reject", response_model=Message)
def reject_evidence(evidence_id: int, db: Session = Depends(get_db)) -> Message:
    record = _record(db, evidence_id); asset = _asset(db, record.asset_id)
    record.evidence_status = "rejected"; record.reviewed_by = "application"; record.reviewed_at = datetime.now(timezone.utc)
    _refresh(asset); apply_assessment(asset); log_event(db, entity_type="asset", entity_id=asset.id, action="evidence_reject", summary=f"Rejected evidence {record.id} for {asset.asset_code}")
    db.commit(); return Message(message=f"Rejected evidence {record.id}")
