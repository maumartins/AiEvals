"""Testes de importação e CRUD de datasets."""

import json

import pytest
from sqlmodel import Session, create_engine, SQLModel

from app.services import datasets as svc


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # Importa todos os modelos para criar tabelas
    from app.models import entities  # noqa
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_create_and_list_datasets(session):
    ds = svc.create_dataset(session, name="Test DS", description="desc", category="cat")
    assert ds.id is not None
    all_ds = svc.list_datasets(session)
    assert len(all_ds) == 1
    assert all_ds[0].name == "Test DS"


def test_create_case(session):
    ds = svc.create_dataset(session, name="DS")
    case = svc.create_case(session, ds.id, {
        "user_input": "Qual é a capital?",
        "expected_answer": "Brasília",
        "scenario_type": "general_qa",
        "severity": "low",
        "tags": ["geo", "brasil"],
    })
    assert case.id is not None
    assert case.user_input == "Qual é a capital?"
    assert case.get_tags() == ["geo", "brasil"]


def test_import_jsonl(session):
    ds = svc.create_dataset(session, name="JSONL DS")
    content = '\n'.join([
        json.dumps({"user_input": f"Pergunta {i}", "scenario_type": "general_qa"})
        for i in range(3)
    ])
    imported, errors = svc.import_jsonl(session, ds.id, content)
    assert imported == 3
    assert errors == []
    assert len(svc.list_cases(session, ds.id)) == 3


def test_import_jsonl_missing_user_input(session):
    ds = svc.create_dataset(session, name="DS2")
    content = json.dumps({"expected_answer": "sem user_input"})
    imported, errors = svc.import_jsonl(session, ds.id, content)
    assert imported == 0
    assert len(errors) == 1
    assert "user_input" in errors[0]


def test_import_csv(session):
    ds = svc.create_dataset(session, name="CSV DS")
    csv_content = "user_input,expected_answer,scenario_type\nO que é Python?,Linguagem de programação,general_qa\nCapital da França?,Paris,general_qa"
    imported, errors = svc.import_csv(session, ds.id, csv_content)
    assert imported == 2
    assert errors == []


def test_import_csv_without_user_input_column(session):
    ds = svc.create_dataset(session, name="CSV Bad")
    csv_content = "pergunta,resposta\nPergunta 1,Resp 1"
    imported, errors = svc.import_csv(session, ds.id, csv_content)
    assert imported == 0
    assert len(errors) > 0


def test_delete_dataset(session):
    ds = svc.create_dataset(session, name="Para deletar")
    svc.create_case(session, ds.id, {"user_input": "teste"})
    result = svc.delete_dataset(session, ds.id)
    assert result is True
    assert svc.get_dataset(session, ds.id) is None
    assert svc.list_cases(session, ds.id) == []


def test_export_jsonl_roundtrip_preserves_case_fields(session):
    ds = svc.create_dataset(session, name="Dataset Exportavel", description="roundtrip")
    svc.create_case(
        session,
        ds.id,
        {
            "name": "Caso exportado",
            "category": "qa",
            "user_input": "Explique o plano de contingencia.",
            "system_prompt": "Responda em bullets.",
            "expected_answer": "Plano com mitigacao e responsaveis.",
            "retrieved_context": "Documento interno v2",
            "reference_context": "Politica corporativa",
            "expected_citations": '["Politica corporativa"]',
            "metadata_json": '{"required_keywords":["mitigacao"]}',
            "scenario_type": "rag_qa",
            "severity": "medium",
            "tags": ["roundtrip", "export"],
        },
    )

    exported = svc.export_dataset_jsonl(session, ds.id)
    ds_copy = svc.create_dataset(session, name="Dataset Reimportado")
    imported, errors = svc.import_jsonl(session, ds_copy.id, exported)

    assert imported == 1
    assert errors == []

    imported_case = svc.list_cases(session, ds_copy.id)[0]
    assert imported_case.name == "Caso exportado"
    assert imported_case.category == "qa"
    assert imported_case.system_prompt == "Responda em bullets."
    assert imported_case.retrieved_context == "Documento interno v2"
    assert imported_case.reference_context == "Politica corporativa"
    assert imported_case.expected_citations == '["Politica corporativa"]'
    assert imported_case.get_tags() == ["roundtrip", "export"]
    assert json.loads(imported_case.metadata_json)["required_keywords"] == ["mitigacao"]


def test_export_csv_contains_expected_columns(session):
    ds = svc.create_dataset(session, name="CSV Export")
    svc.create_case(
        session,
        ds.id,
        {
            "name": "Caso CSV",
            "user_input": "Retorne um JSON simples",
            "expected_answer": '{"ok": true}',
            "scenario_type": "extraction",
            "severity": "low",
        },
    )

    exported = svc.export_dataset_csv(session, ds.id)

    assert "user_input" in exported
    assert "expected_answer" in exported
    assert "scenario_type" in exported
    assert "Caso CSV" in exported
