from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Programme
from app.schemas import Message, ProgrammeCreate, ProgrammeRead, ProgrammeUpdate
from app.services.audit import log_event

router = APIRouter(prefix="/programmes", tags=["programmes"])


def _get_programme_or_404(db: Session, programme_id: int) -> Programme:
    programme = db.scalar(
        select(Programme).options(selectinload(Programme.assets)).where(Programme.id == programme_id)
    )
    if not programme:
        raise HTTPException(status_code=404, detail="Programme not found")
    return programme


def _to_read(programme: Programme) -> ProgrammeRead:
    risks = [asset.risk_score for asset in programme.assets]
    budget = float(programme.budget_estimate or Decimal("0"))
    total_budget = budget * (1 + programme.contingency_percent / 100)
    return ProgrammeRead.model_validate(
        {
            **{column.name: getattr(programme, column.name) for column in Programme.__table__.columns},
            "asset_count": len(programme.assets),
            "critical_assets": sum(1 for asset in programme.assets if asset.risk_band == "Critical"),
            "average_risk": round(sum(risks) / len(risks), 1) if risks else 0,
            "total_budget": round(total_budget, 2),
        }
    )


@router.get("", response_model=list[ProgrammeRead])
def list_programmes(
    status_filter: str | None = Query(default=None, alias="status"),
    target_wave: str | None = None,
    db: Session = Depends(get_db),
) -> list[ProgrammeRead]:
    statement = select(Programme).options(selectinload(Programme.assets))
    if status_filter:
        statement = statement.where(Programme.status == status_filter)
    if target_wave:
        statement = statement.where(Programme.target_wave == target_wave)
    statement = statement.order_by(Programme.target_wave, Programme.package_code)
    return [_to_read(item) for item in db.scalars(statement).all()]


@router.post("", response_model=ProgrammeRead, status_code=status.HTTP_201_CREATED)
def create_programme(payload: ProgrammeCreate, db: Session = Depends(get_db)) -> ProgrammeRead:
    if db.scalar(select(Programme).where(Programme.package_code == payload.package_code)):
        raise HTTPException(status_code=409, detail="package_code already exists")
    programme = Programme(**payload.model_dump())
    db.add(programme)
    db.flush()
    log_event(
        db,
        entity_type="programme",
        entity_id=programme.id,
        action="create",
        summary=f"Created {programme.package_code} · {programme.title}",
    )
    db.commit()
    return _to_read(_get_programme_or_404(db, programme.id))


@router.get("/{programme_id}", response_model=ProgrammeRead)
def get_programme(programme_id: int, db: Session = Depends(get_db)) -> ProgrammeRead:
    return _to_read(_get_programme_or_404(db, programme_id))


@router.patch("/{programme_id}", response_model=ProgrammeRead)
def update_programme(programme_id: int, payload: ProgrammeUpdate, db: Session = Depends(get_db)) -> ProgrammeRead:
    programme = _get_programme_or_404(db, programme_id)
    updates = payload.model_dump(exclude_unset=True)
    if "package_code" in updates and updates["package_code"] != programme.package_code:
        duplicate = db.scalar(select(Programme).where(Programme.package_code == updates["package_code"]))
        if duplicate:
            raise HTTPException(status_code=409, detail="package_code already exists")
    for key, value in updates.items():
        setattr(programme, key, value)
    log_event(
        db,
        entity_type="programme",
        entity_id=programme.id,
        action="update",
        summary=f"Updated {programme.package_code} · {programme.title}",
    )
    db.commit()
    return _to_read(_get_programme_or_404(db, programme.id))


@router.delete("/{programme_id}", response_model=Message)
def delete_programme(programme_id: int, db: Session = Depends(get_db)) -> Message:
    programme = _get_programme_or_404(db, programme_id)
    for asset in programme.assets:
        asset.programme_id = None
    summary = f"Deleted {programme.package_code} · {programme.title}; linked assets were unassigned"
    log_event(db, entity_type="programme", entity_id=programme.id, action="delete", summary=summary)
    db.delete(programme)
    db.commit()
    return Message(message=summary)
