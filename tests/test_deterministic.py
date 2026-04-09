"""Testes de métricas determinísticas."""

import pytest
from unittest.mock import MagicMock

from app.models.entities import RunCaseResult, RunStatus, ScenarioType, Severity, TestCase
from app.services.evaluation.deterministic import (
    _check_json_validity,
    _check_citations,
    _structural_completeness,
    compute_deterministic_metrics,
)


def make_case(
    scenario_type=ScenarioType.general_qa,
    expected_citations=None,
    user_input="Qual é a capital?",
) -> TestCase:
    case = TestCase(
        dataset_id=1,
        user_input=user_input,
        scenario_type=scenario_type,
        severity=Severity.low,
    )
    case.expected_citations = expected_citations
    return case


def make_result(response="Resposta de teste.", latency_ms=250.0, cost_usd=0.001) -> RunCaseResult:
    result = RunCaseResult(run_id=1, test_case_id=1)
    result.response = response
    result.latency_ms = latency_ms
    result.cost_usd = cost_usd
    result.status = RunStatus.completed
    return result


class TestJsonValidity:
    def test_valid_json(self):
        assert _check_json_validity('{"key": "value"}') is True

    def test_valid_json_in_text(self):
        assert _check_json_validity('Aqui está: {"name": "João"}') is True

    def test_valid_json_in_markdown(self):
        assert _check_json_validity('```json\n{"key": "val"}\n```') is True

    def test_invalid_json(self):
        assert _check_json_validity("Esta não é uma resposta JSON") is False

    def test_empty_string(self):
        assert _check_json_validity("") is False


class TestCitationCoverage:
    def test_citation_found(self):
        score = _check_citations("A resposta menciona Python e Django.", '["Python", "Django"]')
        assert score == 1.0

    def test_citation_partially_found(self):
        score = _check_citations("A resposta menciona Python.", '["Python", "Django"]')
        assert score == 0.5

    def test_citation_not_found(self):
        score = _check_citations("A resposta não menciona nada relevante.", '["Python"]')
        assert score == 0.0


class TestStructuralCompleteness:
    def test_empty_response(self):
        assert _structural_completeness("") == 0.0

    def test_short_response(self):
        score = _structural_completeness("Ok.")
        assert score < 0.7

    def test_good_response(self):
        score = _structural_completeness("Esta é uma resposta completa e bem estruturada com pontuação adequada.")
        assert score == 1.0


class TestComputeMetrics:
    def test_all_metrics_returned(self):
        case = make_case()
        result = make_result()
        metrics = compute_deterministic_metrics(case, result)
        names = [m["name"] for m in metrics]
        assert "latency_ms" in names
        assert "latency_score" in names
        assert "cost_usd" in names
        assert "response_length_chars" in names
        assert "is_empty_response" in names
        assert "structural_completeness" in names

    def test_json_validity_skipped_for_general_qa(self):
        case = make_case(scenario_type=ScenarioType.general_qa)
        result = make_result()
        metrics = compute_deterministic_metrics(case, result)
        json_metric = next(m for m in metrics if m["name"] == "json_validity")
        assert json_metric["status"] == "skipped"

    def test_json_validity_computed_for_extraction(self):
        case = make_case(scenario_type=ScenarioType.extraction)
        result = make_result(response='{"key": "value"}')
        metrics = compute_deterministic_metrics(case, result)
        json_metric = next(m for m in metrics if m["name"] == "json_validity")
        assert json_metric["status"] == "computed"
        assert json_metric["value"] == 1.0

    def test_empty_response_flagged(self):
        case = make_case()
        result = make_result(response="")
        metrics = compute_deterministic_metrics(case, result)
        empty_metric = next(m for m in metrics if m["name"] == "is_empty_response")
        assert empty_metric["value"] == 1.0

    def test_citations_skipped_when_no_expected(self):
        case = make_case(expected_citations=None)
        result = make_result()
        metrics = compute_deterministic_metrics(case, result)
        citation_metric = next(m for m in metrics if m["name"] == "citation_coverage")
        assert citation_metric["status"] == "skipped"
