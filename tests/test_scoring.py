"""Testes de score composto."""

import pytest

from app.models.entities import MetricScore, MetricStatus
from app.services.evaluation.scoring import compute_composite_score


def make_metric(name: str, value: float | None, family: str = "deterministic") -> MetricScore:
    m = MetricScore(result_id=1, metric_name=name, metric_family=family)
    m.value = value
    m.status = MetricStatus.computed if value is not None else MetricStatus.skipped
    return m


class TestCompositeScore:
    def test_returns_none_with_no_matching_metrics(self):
        metrics = [make_metric("unknown_metric", 0.5)]
        score = compute_composite_score(metrics, preset="general_assistant")
        assert score is None

    def test_basic_score_computation(self):
        metrics = [
            make_metric("correctness", 4.0),   # judge 1-5 → normalized
            make_metric("helpfulness", 5.0),
            make_metric("clarity", 4.0),
        ]
        score = compute_composite_score(metrics, preset="general_assistant")
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_skipped_metrics_ignored(self):
        metrics = [
            make_metric("correctness", 4.0),
            make_metric("semantic_similarity", None),  # skipped
        ]
        # Só deve usar os que têm valor
        score = compute_composite_score(metrics, preset="general_assistant")
        assert score is not None

    def test_rag_preset(self):
        metrics = [
            make_metric("faithfulness", 0.8, "rag"),
            make_metric("answer_relevancy", 0.7, "rag"),
            make_metric("correctness", 4.0, "judge"),
        ]
        score = compute_composite_score(metrics, preset="rag_grounded_qa")
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_safety_preset_prioritizes_safety(self):
        # Segurança perfeita (5/5) mas correctness ruim (1/5)
        metrics = [
            make_metric("safety", 5.0),
            make_metric("correctness", 1.0),
        ]
        score_safety = compute_composite_score(metrics, preset="safety_first")
        # Safety tem peso 0.5 no preset safety_first
        assert score_safety is not None
        assert score_safety > 0.5  # Deve ser alto por causa do safety

    def test_all_perfect_scores(self):
        metrics = [
            make_metric("correctness", 5.0),
            make_metric("completeness", 5.0),
            make_metric("clarity", 5.0),
            make_metric("helpfulness", 5.0),
            make_metric("instruction_following", 5.0),
            make_metric("semantic_similarity", 1.0),
        ]
        score = compute_composite_score(metrics, preset="general_assistant")
        assert score is not None
        assert score >= 0.99  # Deve ser próximo de 1.0

    def test_clamps_values_above_1(self):
        """Valores normalizados não devem ultrapassar 1.0."""
        metrics = [make_metric("correctness", 5.0)]
        score = compute_composite_score(metrics, preset="general_assistant")
        assert score is None or score <= 1.0
