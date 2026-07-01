from __future__ import annotations
from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from app.schemas import SupportStatus, _strip_string

EvidenceRecordStatus = Literal["candidate", "confirmed", "rejected", "conflict", "expired"]
VisibilityStatus = Literal["active", "hidden", "excluded", "superseded", "decommissioned"]

class SourceColumnDefinition(BaseModel):
    original_header: str
    normalised_key: str
    display_label: str
    data_type: str
    group_name: str
    display_order: int
    visible_by_default: bool = True
    enabled: bool = True
    editable: bool = True
    required_for_manual_create: bool = False

class AssetSourceFieldsRead(BaseModel):
    asset_id: int
    source_record_state: str
    source_workbook: str | None = None
    source_sheet: str | None = None
    source_row: int | None = None
    columns: list[SourceColumnDefinition]
    original: dict[str, Any]
    overrides: dict[str, Any]
    effective: dict[str, Any]
    formulas: dict[str, Any]

class AssetSourceFieldsUpdate(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)

class AssetVisibilityUpdate(BaseModel):
    visibility_status: VisibilityStatus
    visibility_reason: str | None = None
    @field_validator("visibility_reason", mode="before")
    @classmethod
    def strip_reason(cls, value):
        return _strip_string(value)

class ImportPreview(BaseModel):
    rows_received: int
    would_create: int
    would_update: int
    would_fail: int
    detected_source: str
    source_columns: list[str]
    duplicate_source_keys: int
    blank_identity_rows: int
    formula_columns: list[str]
    errors: list[str]

class EvidenceRecordRead(BaseModel):
    id: int
    asset_id: int
    evidence_type: str
    authority: str
    source_name: str
    source_url_or_endpoint: str | None = None
    query_payload: dict[str, Any] | None = None
    response_hash: str | None = None
    retrieved_at: datetime | None = None
    matched_vendor: str | None = None
    matched_product: str | None = None
    matched_version: str | None = None
    lifecycle_status: str | None = None
    support_end_date: date | None = None
    confidence_score: float
    evidence_status: EvidenceRecordStatus
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    notes: str | None = None
    raw_response: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class EvidenceConfirmRequest(BaseModel):
    support_status: SupportStatus | None = None
    support_end_date: date | None = None
    notes: str | None = None
    reviewer: str = "application"
