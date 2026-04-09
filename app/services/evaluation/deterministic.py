"""Métricas determinísticas e estruturais."""

import json
import re
from typing import Optional

from app.models.entities import RunCaseResult, ScenarioType, TestCase


def _metric(name: str, value: Optional[float], details: dict | None = None) -> dict:
    return {"name": name, "value": value, "status": "computed", "details": details or {}}


def _skipped(name: str, reason: str) -> dict:
    return {"name": name, "value": None, "status": "skipped", "skip_reason": reason, "details": {}}


def compute_deterministic_metrics(case: TestCase, result: RunCaseResult) -> list[dict]:
    metrics = []
    response = result.response or ""
    metadata = case.get_metadata()

    # 1. Latência (normalizada 0-1: <500ms=1, >5000ms=0)
    if result.latency_ms is not None:
        latency_score = max(0.0, 1.0 - (result.latency_ms - 500) / 4500)
        metrics.append(_metric("latency_ms", result.latency_ms, {"raw_ms": result.latency_ms}))
        metrics.append(_metric("latency_score", round(min(1.0, latency_score), 3)))
    else:
        metrics.append(_skipped("latency_ms", "Latência não disponível"))
        metrics.append(_skipped("latency_score", "Latência não disponível"))

    # 2. Custo
    if result.cost_usd is not None:
        metrics.append(_metric("cost_usd", result.cost_usd))
    else:
        metrics.append(_skipped("cost_usd", "Custo não disponível para este provider"))

    # 3. Tamanho da resposta
    response_len = len(response)
    metrics.append(_metric("response_length_chars", float(response_len)))

    # 4. Resposta vazia
    is_empty = 1.0 if not response.strip() else 0.0
    metrics.append(_metric("is_empty_response", is_empty))

    # 5. Validade JSON (quando extraction ou schema/formato exigir JSON)
    requires_json = case.scenario_type == ScenarioType.extraction or _requires_json(metadata)
    if requires_json:
        json_valid = _check_json_validity(response)
        metrics.append(_metric("json_validity", 1.0 if json_valid else 0.0, {"valid": json_valid}))
    else:
        metrics.append(_skipped("json_validity", f"Não aplicável para cenário {case.scenario_type.value}"))

    # 6. Citações presentes (quando esperado)
    if case.expected_citations:
        citation_score = _check_citations(response, case.expected_citations)
        metrics.append(_metric("citation_coverage", citation_score, {"expected": case.expected_citations}))
    else:
        metrics.append(_skipped("citation_coverage", "Nenhuma citação esperada definida"))

    # 7. Nota de completude estrutural (heurística simples)
    structural_score = _structural_completeness(response)
    metrics.append(_metric("structural_completeness", structural_score))

    # 8. Comprimento adequado (não muito curto, não excessivamente longo)
    adequacy = _length_adequacy(response, case.scenario_type)
    metrics.append(_metric("length_adequacy", adequacy))

    # 9. Tokens
    if result.tokens_input is not None:
        metrics.append(_metric("prompt_token_count", float(result.tokens_input)))
    else:
        metrics.append(_skipped("prompt_token_count", "Quantidade de tokens de entrada indisponível"))

    if result.tokens_output is not None:
        metrics.append(_metric("response_token_count", float(result.tokens_output)))
    else:
        metrics.append(_skipped("response_token_count", "Quantidade de tokens de saída indisponível"))

    if result.tokens_input is not None and result.tokens_output is not None:
        metrics.append(_metric("total_token_count", float(result.tokens_input + result.tokens_output)))
    else:
        metrics.append(_skipped("total_token_count", "Quantidade total de tokens indisponível"))

    # 10. Regras configuráveis por keyword
    keyword_metric = _keyword_rules_metric(response, metadata)
    if keyword_metric:
        metrics.append(keyword_metric)
    else:
        metrics.append(_skipped("keyword_rule_adherence", "Nenhuma keyword rule configurada"))

    # 11. Regras configuráveis por regex
    regex_metric = _regex_rules_metric(response, metadata)
    if regex_metric:
        metrics.append(regex_metric)
    else:
        metrics.append(_skipped("regex_rule_adherence", "Nenhuma regex rule configurada"))

    return metrics


def _requires_json(metadata: dict) -> bool:
    return bool(
        metadata.get("json_schema_required")
        or metadata.get("require_json_schema")
        or metadata.get("response_format") == "json"
    )


def _check_json_validity(text: str) -> bool:
    """Verifica se o texto contém JSON válido."""
    # Tenta encontrar bloco JSON no texto
    text = text.strip()
    # Remove markdown code blocks
    text = re.sub(r"```(?:json)?\s*", "", text).strip("`").strip()
    try:
        json.loads(text)
        return True
    except Exception:
        # Tenta encontrar JSON embutido
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                json.loads(match.group())
                return True
            except Exception:
                pass
    return False


def _check_citations(response: str, expected_citations: str) -> float:
    """Verifica quantas citações esperadas aparecem na resposta."""
    try:
        expected = json.loads(expected_citations) if expected_citations.startswith("[") else [expected_citations]
    except Exception:
        expected = [expected_citations]

    if not expected:
        return 1.0

    found = sum(1 for cite in expected if str(cite).lower() in response.lower())
    return round(found / len(expected), 3)


def _structural_completeness(response: str) -> float:
    """Heurística simples de completude estrutural."""
    if not response.strip():
        return 0.0
    score = 1.0
    # Penaliza respostas muito curtas (< 20 chars)
    if len(response) < 20:
        score -= 0.4
    # Penaliza se parecer truncado (termina abruptamente sem pontuação)
    if len(response) > 50 and response.strip()[-1] not in ".!?\"':;)]}":
        score -= 0.1
    return round(max(0.0, score), 3)


def _length_adequacy(response: str, scenario_type: ScenarioType) -> float:
    """Avalia se o comprimento é adequado para o tipo de cenário."""
    length = len(response.split())
    targets = {
        ScenarioType.general_qa: (10, 300),
        ScenarioType.rag_qa: (15, 400),
        ScenarioType.summarization: (30, 200),
        ScenarioType.extraction: (5, 150),
        ScenarioType.classification: (5, 100),
        ScenarioType.safety_adversarial: (0, 500),
    }
    min_w, max_w = targets.get(scenario_type, (10, 300))
    if length < min_w:
        return round(length / max(min_w, 1), 3)
    if length > max_w:
        return round(max_w / length, 3)
    return 1.0


def _keyword_rules_metric(response: str, metadata: dict) -> Optional[dict]:
    required = metadata.get("required_keywords") or []
    forbidden = metadata.get("forbidden_keywords") or []
    if not required and not forbidden:
        return None

    response_lower = response.lower()
    matched_required = sum(1 for keyword in required if str(keyword).lower() in response_lower)
    avoided_forbidden = sum(1 for keyword in forbidden if str(keyword).lower() not in response_lower)
    total_rules = len(required) + len(forbidden)
    score = (matched_required + avoided_forbidden) / max(total_rules, 1)
    return _metric(
        "keyword_rule_adherence",
        round(score, 4),
        {
            "required_keywords": required,
            "forbidden_keywords": forbidden,
            "matched_required": matched_required,
            "avoided_forbidden": avoided_forbidden,
        },
    )


def _regex_rules_metric(response: str, metadata: dict) -> Optional[dict]:
    must_match = metadata.get("regex_must_match") or []
    must_not_match = metadata.get("regex_must_not_match") or []
    if isinstance(must_match, str):
        must_match = [must_match]
    if isinstance(must_not_match, str):
        must_not_match = [must_not_match]
    if not must_match and not must_not_match:
        return None

    matched = sum(1 for pattern in must_match if re.search(pattern, response, re.IGNORECASE))
    avoided = sum(1 for pattern in must_not_match if not re.search(pattern, response, re.IGNORECASE))
    total_rules = len(must_match) + len(must_not_match)
    score = (matched + avoided) / max(total_rules, 1)
    return _metric(
        "regex_rule_adherence",
        round(score, 4),
        {
            "regex_must_match": must_match,
            "regex_must_not_match": must_not_match,
            "matched_patterns": matched,
            "avoided_patterns": avoided,
        },
    )
