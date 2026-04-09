"""Testes de rotas HTTP usando banco em memória com StaticPool."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# StaticPool garante que todas as conexões compartilham o mesmo banco em memória
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def _setup_tables():
    from app.models import entities  # noqa — registra as tabelas no metadata
    SQLModel.metadata.create_all(_test_engine)


_setup_tables()


def override_session():
    with Session(_test_engine) as session:
        yield session


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from app.db.engine import get_session

    app.dependency_overrides[get_session] = override_session

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


class TestDashboard:
    def test_dashboard_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_dashboard_has_content(self, client):
        response = client.get("/")
        assert "Dashboard" in response.text or "AI" in response.text


class TestDatasets:
    def test_list_datasets(self, client):
        response = client.get("/datasets/")
        assert response.status_code == 200

    def test_new_dataset_form(self, client):
        response = client.get("/datasets/new")
        assert response.status_code == 200

    def test_create_dataset_redirects(self, client):
        response = client.post(
            "/datasets/",
            data={"name": "Test Route DS", "description": "desc", "category": "test"},
            follow_redirects=False,
        )
        assert response.status_code == 303

    def test_dataset_not_found(self, client):
        response = client.get("/datasets/9999")
        assert response.status_code == 404

    def test_dataset_detail_accessible(self, client):
        # Cria dataset e acessa o detail
        r = client.post(
            "/datasets/",
            data={"name": "DS Para Detail"},
            follow_redirects=True,
        )
        assert r.status_code == 200

    def test_import_invalid_format(self, client):
        from io import BytesIO
        # Garante que existe dataset 1
        client.post("/datasets/", data={"name": "DS Import"}, follow_redirects=False)
        response = client.post(
            "/datasets/1/import",
            files={"file": ("data.txt", BytesIO(b"conteudo"), "text/plain")},
        )
        assert response.status_code == 400


class TestRuns:
    def test_list_runs(self, client):
        response = client.get("/runs/")
        assert response.status_code == 200

    def test_new_run_form(self, client):
        response = client.get("/runs/new")
        assert response.status_code == 200

    def test_run_not_found(self, client):
        response = client.get("/runs/9999")
        assert response.status_code == 404

    def test_compare_form_get(self, client):
        response = client.get("/runs/compare")
        assert response.status_code == 200


class TestSafety:
    def test_safety_dashboard(self, client):
        response = client.get("/safety/")
        assert response.status_code == 200

    def test_safety_shows_content(self, client):
        response = client.get("/safety/")
        assert response.status_code == 200
        # Deve renderizar algum conteúdo
        assert len(response.text) > 100


class TestSettings:
    def test_settings_page(self, client):
        response = client.get("/settings/")
        assert response.status_code == 200

    def test_settings_shows_providers(self, client):
        response = client.get("/settings/")
        assert "mock" in response.text
