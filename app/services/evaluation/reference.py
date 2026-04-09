"""Métricas com referência: similaridade semântica, cobertura de tópicos, divergência crítica."""

import re
from typing import Optional

from app.core.logging import get_logger
from app.models.entities import RunCaseResult, TestCase

logger = get_logger(__name__)

# Tenta importar sentence-transformers (opcional)
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _ST_MODEL: Optional[SentenceTransformer] = None
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    _ST_MODEL = None


def _get_st_model():
    global _ST_MODEL
    if _ST_MODEL is None and _ST_AVAILABLE:
        try:
            _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"Não foi possível carregar SentenceTransformer: {e}")
    return _ST_MODEL


def _metric(name: str, value: float, details: dict | None = None) -> dict:
    return {"name": name, "value": value, "status": "computed", "details": details or {}}


def _skipped(name: str, reason: str) -> dict:
    return {"name": name, "value": None, "status": "skipped", "skip_reason": reason, "details": {}}


def compute_reference_metrics(case: TestCase, result: RunCaseResult) -> list[dict]:
    metrics = []

    if not case.expected_answer:
        skip_msg = "Nenhum expected_answer definido para este caso"
        for name in [
            "semantic_similarity",
            "factual_correctness",
            "topic_coverage",
            "critical_divergence",
            "lexical_overlap",
        ]:
            metrics.append(_skipped(name, skip_msg))
        return metrics

    response = result.response or ""
    expected = case.expected_answer
    reference_text = case.reference_context or case.expected_answer

    # 1. Similaridade semântica com embeddings
    if _ST_AVAILABLE:
        sim = _semantic_similarity(response, expected)
        if sim is not None:
            metrics.append(_metric("semantic_similarity", round(sim, 4)))
        else:
            metrics.append(_skipped("semantic_similarity", "Erro ao calcular embeddings"))
    else:
        # Fallback: similaridade lexical simples
        sim = _lexical_similarity(response, expected)
        metrics.append(_metric(
            "semantic_similarity", round(sim, 4),
            {"note": "sentence-transformers não disponível; usando fallback lexical"}
        ))

    # 2. Overlap lexical (sempre disponível)
    lex_sim = _lexical_similarity(response, expected)
    metrics.append(_metric("lexical_overlap", round(lex_sim, 4)))

    # 3. Factual correctness aproximada contra a referência
    fact_score = _factual_correctness(response, reference_text)
    metrics.append(_metric("factual_correctness", round(fact_score, 4)))

    # 4. Cobertura de tópicos por checklist simples
    topic_score = _topic_coverage(response, expected)
    metrics.append(_metric("topic_coverage", round(topic_score, 4)))

    # 5. Divergência crítica (flag booleana → 0 = diverge, 1 = OK)
    diverges = _detect_critical_divergence(response, expected)
    metrics.append(_metric(
        "critical_divergence",
        0.0 if diverges else 1.0,
        {"diverges": diverges}
    ))

    return metrics


def _semantic_similarity(text1: str, text2: str) -> Optional[float]:
    """Calcula cosine similarity entre dois textos usando sentence-transformers."""
    try:
        import numpy as np
        model = _get_st_model()
        if model is None:
            return None
        embs = model.encode([text1, text2], normalize_embeddings=True)
        return float(np.dot(embs[0], embs[1]))
    except Exception as e:
        logger.warning(f"Erro em semantic_similarity: {e}")
        return None


def _lexical_similarity(text1: str, text2: str) -> float:
    """Overlap de tokens (Jaccard simples)."""
    tokens1 = set(re.findall(r"\w+", text1.lower()))
    tokens2 = set(re.findall(r"\w+", text2.lower()))
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0
    return len(tokens1 & tokens2) / len(tokens1 | tokens2)


def _topic_coverage(response: str, expected: str) -> float:
    """Verifica quantos termos-chave do expected aparecem na resposta."""
    # Remove stopwords simples
    stopwords = {"a", "o", "e", "de", "do", "da", "em", "para", "que", "um", "uma",
                 "the", "a", "an", "is", "are", "was", "were", "be", "been", "of",
                 "in", "to", "for", "with", "on", "at", "by"}
    expected_tokens = [
        t for t in re.findall(r"\w+", expected.lower())
        if t not in stopwords and len(t) > 3
    ]
    if not expected_tokens:
        return 1.0
    # Considera apenas tokens únicos
    unique_expected = list(dict.fromkeys(expected_tokens))[:20]
    found = sum(1 for t in unique_expected if t in response.lower())
    return found / len(unique_expected)


def _detect_critical_divergence(response: str, expected: str) -> bool:
    """Detecta divergência crítica: negação direta de afirmação da referência."""
    # Heurística simples: se expected diz "sim"/"yes" e response diz "não"/"no", ou vice-versa
    negation_pairs = [
        (r"\bsim\b|\byes\b|\bcorreto\b|\bverdadeiro\b", r"\bnão\b|\bno\b|\bfalso\b|\bincorreto\b"),
    ]
    expected_lower = expected.lower()
    response_lower = response.lower()
    for pos, neg in negation_pairs:
        if re.search(pos, expected_lower) and re.search(neg, response_lower):
            return True
        if re.search(neg, expected_lower) and re.search(pos, response_lower):
            return True
    return False


def _factual_correctness(response: str, reference: str) -> float:
    response_lower = response.lower()
    reference_lower = reference.lower()
    response_numbers = re.findall(r"\d+(?:[.,]\d+)?", response_lower)
    reference_numbers = re.findall(r"\d+(?:[.,]\d+)?", reference_lower)

    lexical = _lexical_similarity(response, reference)
    topic = _topic_coverage(response, reference)
    number_score = 1.0
    if reference_numbers:
        matched = sum(1 for number in reference_numbers if number in response_numbers)
        number_score = matched / len(reference_numbers)

    contradiction_penalty = 0.0
    if _detect_critical_divergence(response, reference):
        contradiction_penalty = 0.5

    score = (lexical * 0.35) + (topic * 0.4) + (number_score * 0.25) - contradiction_penalty
    return max(0.0, min(1.0, score))
