"""Métricas de grounding/RAG usando Ragas quando disponível, com fallback léxico."""

import re
from typing import Optional

from app.core.logging import get_logger
from app.models.entities import RunCaseResult, ScenarioType, TestCase

logger = get_logger(__name__)

# Tenta importar ragas (opcional no MVP)
try:
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from ragas import evaluate
    from datasets import Dataset as HFDataset
    _RAGAS_AVAILABLE = True
except ImportError:
    _RAGAS_AVAILABLE = False


def _metric(name: str, value: float, details: dict | None = None) -> dict:
    return {"name": name, "value": value, "status": "computed", "details": details or {}}


def _skipped(name: str, reason: str) -> dict:
    return {"name": name, "value": None, "status": "skipped", "skip_reason": reason, "details": {}}


async def compute_rag_metrics(case: TestCase, result: RunCaseResult) -> list[dict]:
    """Calcula métricas RAG. Usa Ragas se disponível, senão fallback léxico."""
    metrics = []

    if not case.retrieved_context:
        skip_msg = "Nenhum retrieved_context definido para este caso"
        for name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "groundedness"]:
            metrics.append(_skipped(name, skip_msg))
        return metrics

    # Só faz sentido para cenários RAG
    if case.scenario_type not in (ScenarioType.rag_qa, ScenarioType.general_qa):
        skip_msg = f"Métricas RAG não aplicáveis para cenário {case.scenario_type.value}"
        for name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "groundedness"]:
            metrics.append(_skipped(name, skip_msg))
        return metrics

    response = result.response or ""
    context = case.retrieved_context
    question = case.user_input

    if _RAGAS_AVAILABLE and case.expected_answer:
        try:
            ragas_metrics = await _compute_ragas(question, response, context, case.expected_answer)
            metrics.extend(ragas_metrics)
        except Exception as e:
            logger.warning(f"Ragas falhou, usando fallback léxico: {e}")
            metrics.extend(_compute_lexical_rag(question, response, context, case.expected_answer))
    else:
        if _RAGAS_AVAILABLE and not case.expected_answer:
            skip_msg = "Ragas context_recall requer expected_answer; usando fallback parcial"
        else:
            skip_msg = "Ragas não instalado; usando métricas léxicas de fallback"
        metrics.extend(_compute_lexical_rag(question, response, context, case.expected_answer))

    return metrics


async def _compute_ragas(
    question: str, answer: str, context: str, ground_truth: str
) -> list[dict]:
    """Tenta calcular métricas com Ragas."""
    dataset = HFDataset.from_dict({
        "question": [question],
        "answer": [answer],
        "contexts": [[context]],
        "ground_truth": [ground_truth],
    })
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    df = result.to_pandas()
    row = df.iloc[0]
    metrics = []
    mapping = {
        "faithfulness": "faithfulness",
        "answer_relevancy": "answer_relevancy",
        "context_precision": "context_precision",
        "context_recall": "context_recall",
    }
    for ragas_name, metric_name in mapping.items():
        val = row.get(ragas_name)
        if val is not None and not (isinstance(val, float) and str(val) == "nan"):
            metrics.append(_metric(metric_name, round(float(val), 4), {"source": "ragas"}))
        else:
            metrics.append(_skipped(metric_name, "Ragas retornou NaN para esta métrica"))
    return metrics


def _compute_lexical_rag(
    question: str, answer: str, context: str, expected: Optional[str]
) -> list[dict]:
    """Fallback lexical para métricas RAG quando Ragas não está disponível."""
    metrics = []

    # Faithfulness: quanto da resposta está no contexto
    faithfulness_score = _lexical_overlap(answer, context)
    metrics.append(_metric(
        "faithfulness", round(faithfulness_score, 4),
        {"note": "fallback lexical — Ragas não disponível"}
    ))

    # Answer relevancy: quanto da resposta é relevante para a pergunta
    relevancy_score = _lexical_overlap(answer, question)
    metrics.append(_metric(
        "answer_relevancy", round(relevancy_score, 4),
        {"note": "fallback lexical"}
    ))

    # Context precision: quanto do contexto é relevante para a pergunta
    precision_score = _lexical_overlap(context, question)
    metrics.append(_metric(
        "context_precision", round(precision_score, 4),
        {"note": "fallback lexical"}
    ))

    # Context recall: requer ground_truth
    if expected:
        recall_score = _lexical_overlap(context, expected)
        metrics.append(_metric(
            "context_recall", round(recall_score, 4),
            {"note": "fallback lexical"}
        ))
    else:
        metrics.append(_skipped("context_recall", "Requer expected_answer para calcular recall"))

    # Groundedness: heurística — resposta cita termos do contexto
    ground_score = _groundedness(answer, context)
    metrics.append(_metric(
        "groundedness", round(ground_score, 4),
        {"note": "fallback lexical"}
    ))

    return metrics


def _lexical_overlap(text_a: str, text_b: str) -> float:
    """Jaccard de tokens entre dois textos."""
    stopwords = {"a", "o", "e", "de", "do", "the", "is", "are", "in", "to", "of", "for"}
    tok_a = {t for t in re.findall(r"\w+", text_a.lower()) if t not in stopwords and len(t) > 2}
    tok_b = {t for t in re.findall(r"\w+", text_b.lower()) if t not in stopwords and len(t) > 2}
    if not tok_a or not tok_b:
        return 0.0
    return len(tok_a & tok_b) / len(tok_a | tok_b)


def _groundedness(answer: str, context: str) -> float:
    """Verifica se a resposta cita termos importantes do contexto."""
    context_tokens = set(re.findall(r"\w{5,}", context.lower()))
    if not context_tokens:
        return 0.0
    answer_tokens = set(re.findall(r"\w{5,}", answer.lower()))
    if not answer_tokens:
        return 0.0
    overlap = len(context_tokens & answer_tokens)
    return min(1.0, overlap / max(len(context_tokens) * 0.3, 1))
