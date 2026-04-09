"""Engine SQLite e criação de tabelas."""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# Garante que o diretório de dados existe
db_path = settings.database_url.replace("sqlite:///", "")
if db_path.startswith("./"):
    db_path = db_path[2:]
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
