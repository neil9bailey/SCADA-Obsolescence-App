from __future__ import annotations

from app.models import merge_source_payload
from app.services.source_columns import SOURCE_REGISTER_COLUMNS, blank_source_payload


def clean_source_payload(payload):
    if payload is None:
        return None
    merged = blank_source_payload()
    merged.update({key: value for key, value in payload.items() if key in SOURCE_REGISTER_COLUMNS})
    return merged


def sync_source_payload(asset):
    original = clean_source_payload(asset.source_payload_original or asset.source_payload)
    overrides = {key: value for key, value in (asset.source_payload_overrides or {}).items() if key in SOURCE_REGISTER_COLUMNS}
    asset.source_payload_original = original
    asset.source_payload_overrides = overrides or None
    asset.source_payload = merge_source_payload(original, overrides)
    if overrides:
        asset.source_record_state = "imported_with_overrides" if asset.source_workbook else "manual_with_source_fields"
    elif asset.source_workbook:
        asset.source_record_state = "imported"
