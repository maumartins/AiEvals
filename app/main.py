"""Ponto de entrada da aplicação FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import dashboard, datasets, runs, safety, settings_routes
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.engine import create_db_and_tables
from app.services.observability.tracer import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    setup_tracing()
    create_db_and_tables()

    # Seed data se banco estiver vazio
    from app.db.engine import engine
    from sqlmodel import Session, select
    from app.models.entities import Dataset
    with Session(engine) as session:
        count = len(session.exec(select(Dataset)).all())
        if count == 0:
            from scripts.seed import run_seed
            run_seed(session)

    yield


app = FastAPI(
    title="AI Response Quality Lab",
    description="Laboratório de avaliação de qualidade de respostas de IA",
    version="0.1.0",
    lifespan=lifespan,
)

# Static files
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Rotas
app.include_router(dashboard.router)
app.include_router(datasets.router)
app.include_router(runs.router)
app.include_router(safety.router)
app.include_router(settings_routes.router)
