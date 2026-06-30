from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import AUTO_CREATE_SCHEMA, SEED_DEMO
from app.db import get_db
from app.models import Asset, Programme

router = APIRouter(tags=["operations"])


def _database_is_reachable(db: Session) -> bool:
    db.execute(text("SELECT 1"))
    return True


def _asset_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(Asset)) or 0)


def _programme_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(Programme)) or 0)


def _asset_count_where(db: Session, *criteria) -> int:
    return int(db.scalar(select(func.count()).select_from(Asset).where(*criteria)) or 0)


def _programme_count_where(db: Session, *criteria) -> int:
    return int(db.scalar(select(func.count()).select_from(Programme).where(*criteria)) or 0)


@router.get("/admin/health")
def admin_health(db: Session = Depends(get_db)) -> dict:
    _database_is_reachable(db)
    return {
        "status": "ok",
        "database": "reachable",
        "data_source": "relational_database",
    }


@router.get("/trust/status")
def trust_status(db: Session = Depends(get_db)) -> dict:
    _database_is_reachable(db)
    return {
        "status": "ok",
        "trust_status": "trusted",
        "database": "reachable",
        "data_source": "relational_database",
        "demo_seed_enabled": SEED_DEMO,
        "auto_create_schema": AUTO_CREATE_SCHEMA,
    }


@router.get("/admin/metrics", response_class=PlainTextResponse)
def admin_metrics(db: Session = Depends(get_db)) -> PlainTextResponse:
    _database_is_reachable(db)
    metrics = {
        "scada_database_reachable": 1,
        "scada_assets_total": _asset_count(db),
        "scada_high_risk_assets_total": _asset_count_where(
            db,
            Asset.risk_band.in_(("Critical", "High")),
        ),
        "scada_unsupported_assets_total": _asset_count_where(
            db,
            Asset.support_status == "end_of_support",
        ),
        "scada_unknown_lifecycle_assets_total": _asset_count_where(
            db,
            Asset.support_status == "unknown",
        ),
        "scada_programmes_total": _programme_count(db),
        "scada_active_programmes_total": _programme_count_where(
            db,
            Programme.status != "closed",
        ),
        "scada_unassigned_assets_total": _asset_count_where(db, Asset.programme_id.is_(None)),
    }
    body = "\n".join(f"{name} {value}" for name, value in metrics.items()) + "\n"
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4; charset=utf-8")
