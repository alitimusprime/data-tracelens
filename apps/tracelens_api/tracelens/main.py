from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from services.common.observability import instrument_app
from tracelens.api.router import router
from tracelens.config import get_settings
from tracelens.infrastructure.database import SessionLocal
from tracelens.services.catalog import ensure_catalog

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with SessionLocal() as session:
        ensure_catalog(session)
    yield


app = FastAPI(
    title="TraceLens API",
    version="0.1.0",
    description="Evidence-grounded incident investigation for distributed systems",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)
instrument_app(app, "tracelens-api", "0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "tracelens-api"}


@app.get("/ready")
def ready() -> dict[str, str]:
    with SessionLocal() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ready"}
