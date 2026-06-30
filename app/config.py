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
