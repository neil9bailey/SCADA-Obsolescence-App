from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, JSON, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import mapped_column, relationship
from app.db import Base


def utcnow():
    return datetime.now(timezone.utc)


def merge_source_payload(original, overrides):
    if not original and not overrides:
        return None
    merged = dict(original or {})
    merged.update(overrides or {})
    return merged


class Programme(Base):
    __tablename__ = "programmes"
    id = mapped_column(Integer, primary_key=True)
    package_code = mapped_column(String(50), unique=True, index=True)
    title = mapped_column(String(200), index=True)
    description = mapped_column(Text, nullable=True)
    owner = mapped_column(String(120), nullable=True)
    sponsor = mapped_column(String(120), nullable=True)
    status = mapped_column(String(40), default="discovery", index=True)
    target_wave = mapped_column(String(30), default="Unassigned", index=True)
    budget_estimate = mapped_column(Numeric(14, 2), default=0)
    contingency_percent = mapped_column(Float, default=20)
    target_start = mapped_column(Date, nullable=True)
    target_finish = mapped_column(Date, nullable=True)
    outage_window = mapped_column(String(160), nullable=True)
    target_platform = mapped_column(String(200), nullable=True)
    dependencies = mapped_column(Text, nullable=True)
    notes = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    assets = relationship("Asset", back_populates="programme")


class Asset(Base):
    __tablename__ = "assets"
    id = mapped_column(Integer, primary_key=True)
    asset_code = mapped_column(String(80), unique=True, index=True)
    system_name = mapped_column(String(200), index=True)
    site = mapped_column(String(120), index=True)
    process_area = mapped_column(String(160), nullable=True)
    asset_type = mapped_column(String(80), default="Other", index=True)
    manufacturer = mapped_column(String(120), nullable=True)
    model = mapped_column(String(120), nullable=True)
    software_version = mapped_column(String(100), nullable=True)
    firmware_version = mapped_column(String(100), nullable=True)
    os_version = mapped_column(String(120), nullable=True)
    support_status = mapped_column(String(40), default="unknown", index=True)
    support_end_date = mapped_column(Date, nullable=True)
    business_criticality = mapped_column(Integer, default=3)
    safety_impact = mapped_column(Integer, default=3)
    production_impact = mapped_column(Integer, default=3)
    cyber_exposure = mapped_column(Integer, default=3)
    failure_likelihood = mapped_column(Integer, default=3)
    spares_risk = mapped_column(Integer, default=3)
    recoverability_risk = mapped_column(Integer, default=3)
    dependency_complexity = mapped_column(Integer, default=3)
    evidence_confidence = mapped_column(String(1), default="D")
    delivery_readiness = mapped_column(Integer, default=1)
    treatment = mapped_column(String(40), default="assess", index=True)
    owner = mapped_column(String(120), nullable=True)
    notes = mapped_column(Text, nullable=True)
    is_active = mapped_column(Boolean, default=True, index=True)
    visibility_status = mapped_column(String(30), default="active", index=True)
    visibility_reason = mapped_column(Text, nullable=True)
    source_record_state = mapped_column(String(40), default="manually_created", index=True)
    evidence_status = mapped_column(String(40), default="unverified", index=True)
    vendor_evidence_summary = mapped_column(JSON, nullable=True)
    source_workbook = mapped_column(String(260), nullable=True)
    source_sheet = mapped_column(String(120), nullable=True)
    source_row = mapped_column(Integer, nullable=True, index=True)
    source_category = mapped_column(String(80), nullable=True, index=True)
    source_subcategory = mapped_column(String(120), nullable=True, index=True)
    source_payload = mapped_column(JSON, nullable=True)
    source_payload_original = mapped_column(JSON, nullable=True)
    source_payload_overrides = mapped_column(JSON, nullable=True)
    source_formulas = mapped_column(JSON, nullable=True)
    source_intelligence = mapped_column(JSON, nullable=True)
    risk_score = mapped_column(Float, default=0, index=True)
    risk_band = mapped_column(String(20), default="Low", index=True)
    recommended_wave = mapped_column(String(30), default="Monitor", index=True)
    data_completeness = mapped_column(Integer, default=0)
    programme_id = mapped_column(ForeignKey("programmes.id"), nullable=True, index=True)
    programme = relationship("Programme", back_populates="assets")
    evidence_records = relationship("EvidenceRecord", back_populates="asset")
    created_at = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    @property
    def source_payload_effective(self):
        return merge_source_payload(self.source_payload_original or self.source_payload, self.source_payload_overrides)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id = mapped_column(Integer, primary_key=True)
    asset_id = mapped_column(ForeignKey("assets.id"), index=True)
    evidence_type = mapped_column(String(60), index=True)
    authority = mapped_column(String(120), index=True)
    source_name = mapped_column(String(200))
    source_url_or_endpoint = mapped_column(Text, nullable=True)
    query_payload = mapped_column(JSON, nullable=True)
    response_hash = mapped_column(String(128), nullable=True)
    retrieved_at = mapped_column(DateTime(timezone=True), nullable=True)
    matched_vendor = mapped_column(String(120), nullable=True)
    matched_product = mapped_column(String(200), nullable=True)
    matched_version = mapped_column(String(120), nullable=True)
    lifecycle_status = mapped_column(String(40), nullable=True)
    support_end_date = mapped_column(Date, nullable=True)
    confidence_score = mapped_column(Float, default=0)
    evidence_status = mapped_column(String(40), default="candidate", index=True)
    reviewed_by = mapped_column(String(120), nullable=True)
    reviewed_at = mapped_column(DateTime(timezone=True), nullable=True)
    notes = mapped_column(Text, nullable=True)
    raw_response = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    asset = relationship("Asset", back_populates="evidence_records")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = mapped_column(Integer, primary_key=True)
    entity_type = mapped_column(String(40), index=True)
    entity_id = mapped_column(Integer, nullable=True, index=True)
    action = mapped_column(String(40), index=True)
    summary = mapped_column(String(300))
    actor = mapped_column(String(120), default="application")
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
