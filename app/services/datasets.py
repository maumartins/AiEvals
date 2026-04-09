"""Serviço de gerenciamento de datasets, casos e importação/exportação."""

from __future__ import annotations

import csv
import io
import json
from typing import Optional

from sqlmodel import Session, select

from app.core.logging import get_logger
from app.models.entities import Dataset, ScenarioType, Severity, TestCase

logger = get_logger(__name__)


def _normalize_json_list(value) -> str:
    if value is None:
        return "[]"
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    if not text:
        return "[]"
    if text.startswith("["):
        try:
            return json.dumps(json.loads(text), ensure_ascii=False)
        except Exception:
            pass
    return json.dumps([item.strip() for item in text.split(",") if item.strip()], ensure_ascii=False)


def _normalize_json_object(value) -> str:
    if value is None:
        return "{}"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    if not text:
        return "{}"
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    return json.dumps({"raw": text}, ensure_ascii=False)


def create_dataset(session: Session, name: str, description: str = "", category: str = "") -> Dataset:
    dataset = Dataset(name=name, description=description, category=category)
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def update_dataset(session: Session, dataset_id: int, *, name: str, description: str = "", category: str = "") -> Optional[Dataset]:
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        return None
    dataset.name = name
    dataset.description = description
    dataset.category = category
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    return dataset


def list_datasets(session: Session) -> list[Dataset]:
    return list(session.exec(select(Dataset).order_by(Dataset.created_at.desc())).all())


def get_dataset(session: Session, dataset_id: int) -> Optional[Dataset]:
    return session.get(Dataset, dataset_id)


def delete_dataset(session: Session, dataset_id: int) -> bool:
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        return False
    cases = session.exec(select(TestCase).where(TestCase.dataset_id == dataset_id)).all()
    for case in cases:
        session.delete(case)
    session.delete(dataset)
    session.commit()
    return True


def list_cases(session: Session, dataset_id: int) -> list[TestCase]:
    return list(
        session.exec(select(TestCase).where(TestCase.dataset_id == dataset_id).order_by(TestCase.created_at.desc())).all()
    )


def list_cases_by_scenario(session: Session, scenario_type: ScenarioType) -> list[TestCase]:
    return list(
        session.exec(
            select(TestCase).where(TestCase.scenario_type == scenario_type).order_by(TestCase.created_at.desc())
        ).all()
    )


def get_case(session: Session, case_id: int) -> Optional[TestCase]:
    return session.get(TestCase, case_id)


def create_case(session: Session, dataset_id: int, data: dict) -> TestCase:
    tags = _normalize_json_list(data.get("tags", []))
    metadata = _normalize_json_object(data.get("metadata_json", data.get("metadata", {})))
    expected_citations = _normalize_json_list(data.get("expected_citations", []))
    if expected_citations == "[]":
        expected_citations = None

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
        expected_citations=expected_citations,
        metadata_json=metadata,
        severity=Severity(data.get("severity", "low")),
        scenario_type=ScenarioType(data.get("scenario_type", "general_qa")),
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def update_case(session: Session, case_id: int, data: dict) -> Optional[TestCase]:
    case = session.get(TestCase, case_id)
    if not case:
        return None

    case.name = data.get("name", case.name or "")
    case.category = data.get("category", case.category or "")
    case.tags = _normalize_json_list(data.get("tags", case.tags))
    case.user_input = data.get("user_input", case.user_input)
    case.system_prompt = data.get("system_prompt") or None
    case.expected_answer = data.get("expected_answer") or None
    case.retrieved_context = data.get("retrieved_context") or None
    case.reference_context = data.get("reference_context") or None
    expected_citations = _normalize_json_list(data.get("expected_citations", case.expected_citations or []))
    case.expected_citations = None if expected_citations == "[]" else expected_citations
    case.metadata_json = _normalize_json_object(data.get("metadata_json", case.metadata_json))
    case.severity = Severity(data.get("severity", case.severity.value))
    case.scenario_type = ScenarioType(data.get("scenario_type", case.scenario_type.value))
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def delete_case(session: Session, case_id: int) -> bool:
    case = session.get(TestCase, case_id)
    if not case:
        return False
    session.delete(case)
    session.commit()
    return True


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
        except json.JSONDecodeError as exc:
            errors.append(f"Linha {line_num}: JSON inválido — {exc}")
        except Exception as exc:
            errors.append(f"Linha {line_num}: erro — {exc}")
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
            data = {key: (value if value else None) for key, value in row.items()}
            data["user_input"] = row["user_input"]
            create_case(session, dataset_id, data)
            imported += 1
        except Exception as exc:
            errors.append(f"Linha {row_num}: {exc}")
    return imported, errors


def export_dataset_jsonl(session: Session, dataset_id: int) -> str:
    cases = list_cases(session, dataset_id)
    return "\n".join(json.dumps(_serialize_case(case), ensure_ascii=False) for case in cases)


def export_dataset_csv(session: Session, dataset_id: int) -> str:
    cases = list_cases(session, dataset_id)
    headers = [
        "id",
        "name",
        "category",
        "tags",
        "user_input",
        "system_prompt",
        "expected_answer",
        "retrieved_context",
        "reference_context",
        "expected_citations",
        "metadata_json",
        "severity",
        "scenario_type",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for case in cases:
        row = _serialize_case(case)
        row["id"] = case.id
        writer.writerow(row)
    return buffer.getvalue()


def ensure_safety_dataset(session: Session, name: str = "Safety Suite Personalizada") -> Dataset:
    dataset = session.exec(select(Dataset).where(Dataset.name == name)).first()
    if dataset:
        return dataset
    return create_dataset(
        session,
        name=name,
        description="Dataset gerenciável para cenários adversariais e de segurança.",
        category="safety",
    )


def _serialize_case(case: TestCase) -> dict:
    return {
        "name": case.name,
        "category": case.category,
        "tags": case.get_tags(),
        "user_input": case.user_input,
        "system_prompt": case.system_prompt,
        "expected_answer": case.expected_answer,
        "retrieved_context": case.retrieved_context,
        "reference_context": case.reference_context,
        "expected_citations": json.loads(case.expected_citations) if case.expected_citations else [],
        "metadata_json": case.get_metadata(),
        "severity": case.severity.value,
        "scenario_type": case.scenario_type.value,
    }
