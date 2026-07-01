from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = os.getenv("APP_NAME", "SCADA Lifecycle Command Centre")
API_PREFIX = "/api"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+pysqlite:///{(DATA_DIR / 'scada_obsolescence.db').as_posix()}",
)
SEED_DEMO = os.getenv("SEED_DEMO", "true").lower() in {"1", "true", "yes", "on"}
AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", "true").lower() in {"1", "true", "yes", "on"}

# Vendor/evidence automation is deliberately opt-in. When disabled, the evidence
# service creates auditable query plans/candidates but does not claim a lifecycle
# status as confirmed.
ENABLE_VENDOR_LOOKUPS = os.getenv("ENABLE_VENDOR_LOOKUPS", "false").lower() in {"1", "true", "yes", "on"}
VENDOR_LOOKUP_TIMEOUT_SECONDS = float(os.getenv("VENDOR_LOOKUP_TIMEOUT_SECONDS", "8"))
CISCO_SUPPORT_ACCESS_TOKEN = os.getenv("CISCO_SUPPORT_ACCESS_TOKEN")
NVD_API_KEY = os.getenv("NVD_API_KEY")
