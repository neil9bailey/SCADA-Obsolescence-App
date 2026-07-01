from __future__ import annotations
from collections import Counter, defaultdict
import csv, io
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Asset
from app.schemas_live import ImportPreview
from app.services.live_register_import import is_live_register_fieldnames, live_register_natural_key, map_live_register_row, read_live_register_workbook
from app.services.source_columns import SOURCE_REGISTER_COLUMNS

router = APIRouter(prefix="/assets", tags=["assets"])

def _rows(contents: bytes, filename: str):
    if filename.lower().endswith(".xlsx"):
        return read_live_register_workbook(contents, filename), True, SOURCE_REGISTER_COLUMNS
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = [name.strip().lstrip("\ufeff") for name in reader.fieldnames or []]
    live = is_live_register_fieldnames(fieldnames)
    if not fieldnames or ("asset_code" not in fieldnames and not live):
        raise HTTPException(status_code=400, detail="CSV must contain an asset_code column or recognised live obsolescence register columns")
    rows = [{"row": raw, "line_number": line, "source_workbook": filename if live else None, "source_sheet": "CSV" if live else None, "source_row": line if live else None, "source_payload": None, "source_formulas": None} for line, raw in enumerate(reader, start=2)]
    return rows, live, fieldnames

def _normalise(raw: dict[str, Any], *, line_number: int, duplicate_index: int = 1, **source):
    row = {}
    for key, value in raw.items():
        if key is None:
            continue
        clean_key = key.strip().lstrip("\ufeff")
        if isinstance(value, str):
            value = value.strip()
        row[clean_key] = None if value == "" else value
    if "asset_code" not in row and is_live_register_fieldnames(list(row)):
        row = map_live_register_row(row, line_number=line_number, duplicate_index=duplicate_index, **source)
    return row

@router.post("/import/preview", response_model=ImportPreview)
async def preview_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Upload a CSV file or recognised TPCMS workbook")
    import_rows, live, fields = _rows(await file.read(), file.filename)
    dupes, indexes, errors = Counter(), defaultdict(int), []
    would_create = would_update = would_fail = blank_identity_rows = 0
    formula_columns = set()
    for item in import_rows:
        raw, line = item["row"], int(item["line_number"])
        try:
            duplicate_index = 1
            if live:
                natural_key = live_register_natural_key({k.strip().lstrip("\ufeff"): v for k, v in raw.items() if k is not None})
                dupes[natural_key] += 1
                indexes[natural_key] += 1
                duplicate_index = indexes[natural_key]
                if not any(natural_key):
                    blank_identity_rows += 1
            row = _normalise(raw, line_number=line, duplicate_index=duplicate_index, source_workbook=item.get("source_workbook"), source_sheet=item.get("source_sheet"), source_row=item.get("source_row"), source_payload=item.get("source_payload"), source_formulas=item.get("source_formulas"))
            if not row.get("asset_code"):
                raise ValueError("asset_code is required")
            exists = db.scalar(select(Asset).where(Asset.asset_code == str(row["asset_code"])))
            would_update += 1 if exists else 0
            would_create += 0 if exists else 1
            formula_columns.update((item.get("source_formulas") or {}).keys())
        except (ValidationError, ValueError, TypeError) as exc:
            would_fail += 1
            errors.append(f"Row {line}: {str(exc).replace(chr(10), ' ')[:220]}")
    return ImportPreview(rows_received=len(import_rows), would_create=would_create, would_update=would_update, would_fail=would_fail, detected_source="TPCMS live register" if live else "platform CSV", source_columns=fields, duplicate_source_keys=sum(1 for count in dupes.values() if count > 1), blank_identity_rows=blank_identity_rows, formula_columns=sorted(formula_columns), errors=errors[:25])
