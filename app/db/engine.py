"""Engine SQLite, sessões e migrações leves."""

from pathlib import Path

from sqlalchemy.engine import Engine
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
    _run_lightweight_migrations(engine)


def get_session():
    with Session(engine) as session:
        yield session


def session_scope(engine_override: Engine | None = None) -> Session:
    return Session(engine_override or engine)


def _run_lightweight_migrations(active_engine: Engine) -> None:
    if not str(active_engine.url).startswith("sqlite"):
        return

    columns_to_add = {
        "experiment_runs": {
            "rubric_preset": "TEXT DEFAULT 'balanced'",
            "prompt_version": "TEXT DEFAULT 'ad-hoc'",
        },
        "run_case_results": {
            "prompt_version": "TEXT DEFAULT 'ad-hoc'",
        },
    }

    with active_engine.begin() as conn:
        for table_name, table_columns in columns_to_add.items():
            existing = {
                row[1]
                for row in conn.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
            }
            for column_name, ddl in table_columns.items():
                if column_name not in existing:
                    conn.exec_driver_sql(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"
                    )
