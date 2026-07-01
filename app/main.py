from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import API_PREFIX, APP_NAME, AUTO_CREATE_SCHEMA, SEED_DEMO
from app.db import SessionLocal, init_db
from app.routers import assets, assets_controls, dashboard, evidence, health, operations, programmes
from app.seed import seed_demo_data

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    if AUTO_CREATE_SCHEMA:
        init_db()
    if SEED_DEMO:
        with SessionLocal() as db:
            seed_demo_data(db)
    yield


app = FastAPI(
    title=APP_NAME,
    version="0.2.0",
    description="Dynamic SCADA obsolescence portfolio and programme management MVP.",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=None,
    openapi_url=f"{API_PREFIX}/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith(("/api", "/admin", "/trust")):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(health.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(assets_controls.router, prefix=API_PREFIX)
app.include_router(assets.router, prefix=API_PREFIX)
app.include_router(programmes.router, prefix=API_PREFIX)
app.include_router(evidence.router, prefix=API_PREFIX)
app.include_router(operations.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/meta", include_in_schema=False)
def meta() -> dict:
    return {
        "name": APP_NAME,
        "version": app.version,
        "demo_seed_enabled": SEED_DEMO,
        "auto_create_schema": AUTO_CREATE_SCHEMA,
        "data_source": "relational_database",
    }
