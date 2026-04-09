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
