"""Serviço de gerenciamento de datasets e importação."""

import csv
import io
import json
from typing import Optional

from sqlmodel import Session, select

from app.core.logging import get_logger
from app.models.entities import Dataset, ScenarioType, Severity, TestCase

logger = get_logger(__name__)


def create_dataset(session: Session, name: str, description: str = "", category: str = "") -> Dataset:
    dataset = Dataset(name=name, description=description, category=category)
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def list_datasets(session: Session) -> list[Dataset]:
    return list(session.exec(select(Dataset)).all())


def get_dataset(session: Session, dataset_id: int) -> Optional[Dataset]:
    return session.get(Dataset, dataset_id)


def delete_dataset(session: Session, dataset_id: int) -> bool:
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        return False
    # Cascata manual para evitar FK issues no SQLite
    cases = session.exec(select(TestCase).where(TestCase.dataset_id == dataset_id)).all()
    for c in cases:
        session.delete(c)
    session.delete(dataset)
    session.commit()
    return True


def list_cases(session: Session, dataset_id: int) -> list[TestCase]:
    return list(session.exec(select(TestCase).where(TestCase.dataset_id == dataset_id)).all())


def create_case(session: Session, dataset_id: int, data: dict) -> TestCase:
    tags = data.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags)
    meta = data.get("metadata_json", data.get("metadata", {}))
    if isinstance(meta, dict):
        meta = json.dumps(meta)

    case = TestCase(
        dataset_id=dataset_id,
        name=data.get("name", ""),
        category=data.get("category", ""),
        tags=tags,
        user_input=data["user_input"],
        system_prompt=data.get("system_prompt"),
        expected_answer=data.get("expected_answer"),
        retrieved_context=data.get("retrieved_context"),
        reference_context=data.get("reference_context"),
        expected_citations=data.get("expected_citations"),
        metadata_json=meta,
        severity=Severity(data.get("severity", "low")),
        scenario_type=ScenarioType(data.get("scenario_type", "general_qa")),
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def import_jsonl(session: Session, dataset_id: int, content: str) -> tuple[int, list[str]]:
    """Importa casos de JSONL. Retorna (sucessos, erros)."""
    imported = 0
    errors = []
    for line_num, line in enumerate(content.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if "user_input" not in data:
                errors.append(f"Linha {line_num}: campo 'user_input' obrigatório ausente")
                continue
            create_case(session, dataset_id, data)
            imported += 1
        except json.JSONDecodeError as e:
            errors.append(f"Linha {line_num}: JSON inválido — {e}")
        except Exception as e:
            errors.append(f"Linha {line_num}: erro — {e}")
    return imported, errors


def import_csv(session: Session, dataset_id: int, content: str) -> tuple[int, list[str]]:
    """Importa casos de CSV. Retorna (sucessos, erros)."""
    imported = 0
    errors = []
    reader = csv.DictReader(io.StringIO(content))
    if "user_input" not in (reader.fieldnames or []):
        return 0, ["CSV deve ter coluna 'user_input'"]
    for row_num, row in enumerate(reader, 2):
        try:
            # Converte colunas opcionais vazias para None
            data = {k: (v if v else None) for k, v in row.items()}
            data["user_input"] = row["user_input"]
            create_case(session, dataset_id, data)
            imported += 1
        except Exception as e:
            errors.append(f"Linha {row_num}: {e}")
    return imported, errors
