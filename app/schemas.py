from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SupportStatus = Literal["supported", "limited", "end_of_support", "unknown"]
RiskBand = Literal["Low", "Medium", "High", "Critical"]
EvidenceConfidence = Literal["A", "B", "C", "D"]


def _strip_string(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class AssetBase(BaseModel):
    asset_code: str = Field(min_length=1, max_length=80)
    system_name: str = Field(min_length=1, max_length=200)
    site: str = Field(min_length=1, max_length=120)
    process_area: str | None = None
    asset_type: str = "Other"
    manufacturer: str | None = None
    model: str | None = None
    software_version: str | None = None
    firmware_version: str | None = None
    os_version: str | None = None
    support_status: SupportStatus = "unknown"
    support_end_date: date | None = None
    business_criticality: int = Field(default=3, ge=1, le=5)
    safety_impact: int = Field(default=3, ge=1, le=5)
    production_impact: int = Field(default=3, ge=1, le=5)
    cyber_exposure: int = Field(default=3, ge=1, le=5)
    failure_likelihood: int = Field(default=3, ge=1, le=5)
    spares_risk: int = Field(default=3, ge=1, le=5)
    recoverability_risk: int = Field(default=3, ge=1, le=5)
    dependency_complexity: int = Field(default=3, ge=1, le=5)
    evidence_confidence: EvidenceConfidence = "D"
    delivery_readiness: int = Field(default=1, ge=1, le=5)
    treatment: str = "assess"
    owner: str | None = None
    notes: str | None = None
    programme_id: int | None = Field(default=None, ge=1)

    @field_validator(
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
        "treatment",
        "owner",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value):
        return _strip_string(value)


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_code: str | None = Field(default=None, min_length=1, max_length=80)
    system_name: str | None = Field(default=None, min_length=1, max_length=200)
    site: str | None = Field(default=None, min_length=1, max_length=120)
    process_area: str | None = None
    asset_type: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    software_version: str | None = None
    firmware_version: str | None = None
    os_version: str | None = None
    support_status: SupportStatus | None = None
    support_end_date: date | None = None
    business_criticality: int | None = Field(default=None, ge=1, le=5)
    safety_impact: int | None = Field(default=None, ge=1, le=5)
    production_impact: int | None = Field(default=None, ge=1, le=5)
    cyber_exposure: int | None = Field(default=None, ge=1, le=5)
    failure_likelihood: int | None = Field(default=None, ge=1, le=5)
    spares_risk: int | None = Field(default=None, ge=1, le=5)
    recoverability_risk: int | None = Field(default=None, ge=1, le=5)
    dependency_complexity: int | None = Field(default=None, ge=1, le=5)
    evidence_confidence: EvidenceConfidence | None = None
    delivery_readiness: int | None = Field(default=None, ge=1, le=5)
    treatment: str | None = None
    owner: str | None = None
    notes: str | None = None
    programme_id: int | None = Field(default=None, ge=1)

    @field_validator(
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
        "treatment",
        "owner",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value):
        return _strip_string(value)

    @model_validator(mode="after")
    def required_strings_cannot_be_cleared(self):
        for field in ("asset_code", "system_name", "site"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be blank")
        return self


class AssetRead(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    risk_score: float
    risk_band: RiskBand
    recommended_wave: str
    data_completeness: int
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    items: list[AssetRead]
    total: int
    offset: int
    limit: int


class ProgrammeBase(BaseModel):
    package_code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    owner: str | None = None
    sponsor: str | None = None
    status: str = "discovery"
    target_wave: str = "Unassigned"
    budget_estimate: Decimal = Field(default=Decimal("0"), ge=0)
    contingency_percent: float = Field(default=20, ge=0, le=100)
    target_start: date | None = None
    target_finish: date | None = None
    outage_window: str | None = None
    target_platform: str | None = None
    dependencies: str | None = None
    notes: str | None = None

    @field_validator(
        "package_code",
        "title",
        "description",
        "owner",
        "sponsor",
        "status",
        "target_wave",
        "outage_window",
        "target_platform",
        "dependencies",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value):
        return _strip_string(value)


class ProgrammeCreate(ProgrammeBase):
    pass


class ProgrammeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_code: str | None = None
    title: str | None = None
    description: str | None = None
    owner: str | None = None
    sponsor: str | None = None
    status: str | None = None
    target_wave: str | None = None
    budget_estimate: Decimal | None = Field(default=None, ge=0)
    contingency_percent: float | None = Field(default=None, ge=0, le=100)
    target_start: date | None = None
    target_finish: date | None = None
    outage_window: str | None = None
    target_platform: str | None = None
    dependencies: str | None = None
    notes: str | None = None

    @field_validator(
        "package_code",
        "title",
        "description",
        "owner",
        "sponsor",
        "status",
        "target_wave",
        "outage_window",
        "target_platform",
        "dependencies",
        "notes",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, value):
        return _strip_string(value)

    @model_validator(mode="after")
    def required_strings_cannot_be_cleared(self):
        for field in ("package_code", "title"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be blank")
        return self


class ProgrammeRead(ProgrammeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_count: int = 0
    critical_assets: int = 0
    average_risk: float = 0
    total_budget: float = 0
    created_at: datetime
    updated_at: datetime


class ImportResult(BaseModel):
    rows_received: int
    created: int
    updated: int
    failed: int
    errors: list[str]


class Message(BaseModel):
    message: str
