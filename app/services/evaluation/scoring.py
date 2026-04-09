"""Score composto configurável por preset."""

from typing import Optional

from app.models.entities import MetricScore

# Pesos por preset (metric_name → weight)
PRESET_WEIGHTS: dict[str, dict[str, float]] = {
    "general_assistant": {
        "correctness": 0.25,
        "completeness": 0.20,
        "clarity": 0.15,
        "helpfulness": 0.20,
        "instruction_following": 0.10,
        "semantic_similarity": 0.10,
    },
    "rag_grounded_qa": {
        "faithfulness": 0.30,
        "groundedness": 0.20,
        "context_recall": 0.20,
        "answer_relevancy": 0.15,
        "correctness": 0.15,
    },
    "safety_first": {
        "safety": 0.50,
        "correctness": 0.20,
        "instruction_following": 0.20,
        "helpfulness": 0.10,
    },
    "extraction_structured": {
        "json_validity": 0.35,
        "correctness": 0.25,
        "completeness": 0.20,
        "instruction_following": 0.20,
    },
}

# Normalização de métricas do judge (1-5 → 0-1)
JUDGE_METRICS = {
    "correctness", "completeness", "clarity", "helpfulness",
    "safety", "instruction_following",
}


def compute_composite_score(
    metrics: list[MetricScore],
    preset: str = "general_assistant",
) -> Optional[float]:
    """Calcula score composto ignorando métricas SKIPPED.

    Retorna None se não houver métricas suficientes.
    """
    weights = PRESET_WEIGHTS.get(preset, PRESET_WEIGHTS["general_assistant"])
    metric_map = {m.metric_name: m for m in metrics}

    total_weight = 0.0
    weighted_sum = 0.0

    # Adiciona scores do judge se disponíveis (via JudgeResult → MetricScore não existe,
    # mas o judge salva em JudgeResult; aqui mapeamos pelo nome)
    for metric_name, weight in weights.items():
        if metric_name not in metric_map:
            continue
        score = metric_map[metric_name]
        if score.value is None:
            continue

        value = score.value
        # Normaliza métricas do judge de 1-5 para 0-1
        if metric_name in JUDGE_METRICS and value > 1.0:
            value = (value - 1.0) / 4.0

        # Clamp 0-1
        value = max(0.0, min(1.0, value))

        weighted_sum += value * weight
        total_weight += weight

    if total_weight < 0.1:
        return None

    # Normaliza pelo peso total real (métricas disponíveis)
    return round(weighted_sum / total_weight, 4)


def get_judge_metric_scores_from_judge_result(judge_result) -> list[dict]:
    """Extrai métricas do JudgeResult como lista de dicts para uso no scoring."""
    if not judge_result:
        return []
    fields = ["correctness", "completeness", "clarity", "helpfulness", "safety", "instruction_following"]
    return [
        {"name": field, "value": getattr(judge_result, field), "status": "computed"}
        for field in fields
        if getattr(judge_result, field) is not None
    ]
