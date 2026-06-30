from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditEvent


def log_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int | None,
    action: str,
    summary: str,
    actor: str = "application",
) -> None:
    db.add(
        AuditEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            summary=summary[:300],
            actor=actor,
        )
    )
