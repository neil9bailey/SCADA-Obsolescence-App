from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sponsor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="discovery", index=True)
    target_wave: Mapped[str] = mapped_column(String(30), default="Unassigned", index=True)
    budget_estimate: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    contingency_percent: Mapped[float] = mapped_column(Float, default=20)
    target_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    outage_window: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_platform: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dependencies: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    assets: Mapped[list["Asset"]] = relationship(back_populates="programme")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    system_name: Mapped[str] = mapped_column(String(200), index=True)
    site: Mapped[str] = mapped_column(String(120), index=True)
    process_area: Mapped[str | None] = mapped_column(String(160), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(80), default="Other", index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    software_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    support_status: Mapped[str] = mapped_column(String(40), default="unknown", index=True)
    support_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    business_criticality: Mapped[int] = mapped_column(Integer, default=3)
    safety_impact: Mapped[int] = mapped_column(Integer, default=3)
    production_impact: Mapped[int] = mapped_column(Integer, default=3)
    cyber_exposure: Mapped[int] = mapped_column(Integer, default=3)
    failure_likelihood: Mapped[int] = mapped_column(Integer, default=3)
    spares_risk: Mapped[int] = mapped_column(Integer, default=3)
    recoverability_risk: Mapped[int] = mapped_column(Integer, default=3)
    dependency_complexity: Mapped[int] = mapped_column(Integer, default=3)
    evidence_confidence: Mapped[str] = mapped_column(String(1), default="D")
    delivery_readiness: Mapped[int] = mapped_column(Integer, default=1)
    treatment: Mapped[str] = mapped_column(String(40), default="assess", index=True)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_score: Mapped[float] = mapped_column(Float, default=0, index=True)
    risk_band: Mapped[str] = mapped_column(String(20), default="Low", index=True)
    recommended_wave: Mapped[str] = mapped_column(String(30), default="Monitor", index=True)
    data_completeness: Mapped[int] = mapped_column(Integer, default=0)

    programme_id: Mapped[int | None] = mapped_column(ForeignKey("programmes.id", ondelete="SET NULL"), nullable=True, index=True)
    programme: Mapped[Programme | None] = relationship(back_populates="assets")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(String(300))
    actor: Mapped[str] = mapped_column(String(120), default="application")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
