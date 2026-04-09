"""Catálogo de apresentação da UI em Português do Brasil."""

from __future__ import annotations

from typing import Any


METRIC_CATALOG: dict[str, dict[str, str]] = {
    "latency_ms": {
        "label": "Latência (ms)",
        "description": "Tempo total para gerar a resposta do modelo.",
        "guidance": "Menor é melhor.",
        "direction": "lower",
    },
    "latency_score": {
        "label": "Score de Latência",
        "description": "Normalização da latência em escala de 0 a 1.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "cost_usd": {
        "label": "Custo (USD)",
        "description": "Custo estimado da chamada ao modelo.",
        "guidance": "Menor é melhor.",
        "direction": "lower",
    },
    "response_length_chars": {
        "label": "Tamanho da Resposta (caracteres)",
        "description": "Quantidade de caracteres da resposta gerada.",
        "guidance": "Depende do cenário. Compare com respostas equivalentes.",
        "direction": "contextual",
    },
    "is_empty_response": {
        "label": "Resposta Vazia",
        "description": "Indica se o modelo retornou resposta vazia.",
        "guidance": "0 é melhor. 1 indica falha ou recusa sem conteúdo útil.",
        "direction": "lower",
    },
    "json_validity": {
        "label": "JSON Válido",
        "description": "Verifica se a saída contém JSON válido quando isso é esperado.",
        "guidance": "Maior é melhor. 1 significa válido.",
        "direction": "higher",
    },
    "citation_coverage": {
        "label": "Cobertura de Citações",
        "description": "Percentual de citações esperadas que apareceu na resposta.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "structural_completeness": {
        "label": "Completude Estrutural",
        "description": "Heurística simples para verificar se a resposta parece completa e bem encerrada.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "length_adequacy": {
        "label": "Adequação de Tamanho",
        "description": "Avalia se a resposta está curta ou longa demais para o cenário.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "keyword_rule_adherence": {
        "label": "Aderência a Palavras-chave",
        "description": "Verifica se palavras-chave obrigatórias aparecem e palavras proibidas não aparecem.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "regex_rule_adherence": {
        "label": "Aderência a Regras Regex",
        "description": "Valida padrões obrigatórios e padrões proibidos definidos no caso de teste.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "prompt_token_count": {
        "label": "Tokens do Prompt",
        "description": "Quantidade de tokens consumidos pela pergunta/contexto enviados ao modelo.",
        "guidance": "Em geral, menor reduz custo e latência. Compare com execuções equivalentes.",
        "direction": "contextual",
    },
    "response_token_count": {
        "label": "Tokens da Resposta",
        "description": "Quantidade de tokens gerados pelo modelo na resposta.",
        "guidance": "Em geral, menor reduz custo, mas depende da tarefa.",
        "direction": "contextual",
    },
    "total_token_count": {
        "label": "Tokens Totais",
        "description": "Soma dos tokens de entrada e saída desta execução.",
        "guidance": "Em geral, menor reduz custo e latência. Compare com tarefas do mesmo tipo.",
        "direction": "contextual",
    },
    "semantic_similarity": {
        "label": "Similaridade Semântica",
        "description": "Proximidade de sentido entre a resposta e a referência esperada.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "lexical_overlap": {
        "label": "Sobreposição Lexical",
        "description": "Similaridade de palavras entre a resposta e a referência.",
        "guidance": "Maior é melhor, mas não garante correção factual.",
        "direction": "higher",
    },
    "factual_correctness": {
        "label": "Correção Factual",
        "description": "Heurística para verificar aderência factual à referência.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "topic_coverage": {
        "label": "Cobertura de Tópicos",
        "description": "Quanto dos tópicos importantes da referência aparece na resposta.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "critical_divergence": {
        "label": "Sem Divergência Crítica",
        "description": "Sinaliza se a resposta evitou contradições graves com a referência.",
        "guidance": "Maior é melhor. 1 significa sem divergência crítica.",
        "direction": "higher",
    },
    "faithfulness": {
        "label": "Fidelidade ao Contexto",
        "description": "Indica se a resposta está de fato apoiada no contexto recuperado.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "answer_relevancy": {
        "label": "Relevância da Resposta",
        "description": "Avalia o quanto a resposta está alinhada com a pergunta feita.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "context_precision": {
        "label": "Precisão do Contexto",
        "description": "Quanto do contexto recuperado parece realmente útil para responder a pergunta.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "context_recall": {
        "label": "Cobertura do Contexto",
        "description": "Quanto do necessário para responder parece estar coberto pelo contexto recuperado.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "groundedness": {
        "label": "Ancoragem no Contexto",
        "description": "Verifica se a resposta reutiliza evidências do contexto em vez de improvisar.",
        "guidance": "Maior é melhor.",
        "direction": "higher",
    },
    "correctness": {
        "label": "Correção",
        "description": "Nota do judge para precisão factual e aderência ao conteúdo esperado.",
        "guidance": "Maior é melhor. Escala de 1 a 5.",
        "direction": "higher",
    },
    "completeness": {
        "label": "Completude",
        "description": "Nota do judge para cobertura dos pontos importantes da tarefa.",
        "guidance": "Maior é melhor. Escala de 1 a 5.",
        "direction": "higher",
    },
    "clarity": {
        "label": "Clareza",
        "description": "Nota do judge para organização e entendimento da resposta.",
        "guidance": "Maior é melhor. Escala de 1 a 5.",
        "direction": "higher",
    },
    "helpfulness": {
        "label": "Utilidade",
        "description": "Nota do judge para valor prático da resposta ao usuário.",
        "guidance": "Maior é melhor. Escala de 1 a 5.",
        "direction": "higher",
    },
    "safety": {
        "label": "Segurança",
        "description": "Nota do judge para comportamento seguro, recusas adequadas e ausência de conteúdo problemático.",
        "guidance": "Maior é melhor. Escala de 1 a 5.",
        "direction": "higher",
    },
    "instruction_following": {
        "label": "Seguiu as Instruções",
        "description": "Nota do judge para aderência ao formato e às instruções da tarefa.",
        "guidance": "Maior é melhor. Escala de 1 a 5.",
        "direction": "higher",
    },
    "safety_suite_pass": {
        "label": "Passou na Segurança",
        "description": "Sinaliza se o caso adversarial foi tratado de forma segura.",
        "guidance": "Maior é melhor. 1 significa que passou.",
        "direction": "higher",
    },
    "composite_score": {
        "label": "Score Composto",
        "description": "Resumo ponderado do preset selecionado. Não substitui a leitura das métricas individuais.",
        "guidance": "Maior é melhor, mas use apenas como visão resumida.",
        "direction": "higher",
    },
}

SCENARIO_LABELS = {
    "general_qa": "Perguntas Gerais",
    "rag_qa": "RAG / QA com Contexto",
    "summarization": "Sumarização",
    "extraction": "Extração Estruturada",
    "classification": "Classificação",
    "safety_adversarial": "Segurança / Adversarial",
}

SEVERITY_LABELS = {
    "low": "Baixa",
    "medium": "Média",
    "high": "Alta",
}

STATUS_LABELS = {
    "pending": "Pendente",
    "running": "Em execução",
    "completed": "Concluído",
    "failed": "Falhou",
}

PRESET_LABELS = {
    "general_assistant": "Assistente Geral",
    "rag_grounded_qa": "RAG com Grounding",
    "safety_first": "Segurança em Primeiro Lugar",
    "extraction_structured": "Extração / Saída Estruturada",
}

RUBRIC_LABELS = {
    "balanced": "Equilibrada",
    "strict_grounded": "Grounding Estrito",
    "safety_first": "Foco em Segurança",
    "structured_output": "Saída Estruturada",
}


def metric_meta(name: str) -> dict[str, str]:
    return METRIC_CATALOG.get(
        name,
        {
            "label": name,
            "description": "Métrica sem descrição cadastrada.",
            "guidance": "Consulte a documentação.",
            "direction": "contextual",
        },
    )


def metric_label(name: str) -> str:
    return metric_meta(name)["label"]


def metric_tooltip(name: str) -> str:
    meta = metric_meta(name)
    return f'{meta["description"]} Como interpretar: {meta["guidance"]}'


def metric_value_class(value: Any, name: str) -> str:
    meta = metric_meta(name)
    direction = meta["direction"]
    if value is None or direction == "contextual":
        return "text-slate-700"

    try:
        numeric = float(value)
    except Exception:
        return "text-slate-700"

    # latency_ms está em milissegundos — usa thresholds específicos
    if name == "latency_ms":
        if numeric <= 500:
            return "text-green-600 font-semibold"
        if numeric <= 2000:
            return "text-amber-600"
        return "text-red-600"

    if direction == "lower":
        if numeric <= 0.2:
            return "text-green-600 font-semibold"
        if numeric <= 0.6:
            return "text-amber-600"
        return "text-red-600"

    if numeric >= 0.8:
        return "text-green-600 font-semibold"
    if numeric >= 0.5:
        return "text-amber-600"
    return "text-red-600"


def metric_display_value(name: str, value: Any) -> str:
    if value is None:
        return "—"

    if name in {"prompt_token_count", "response_token_count", "total_token_count"}:
        return str(int(value))
    if name == "latency_ms":
        return f"{float(value):.1f}"
    if name == "cost_usd":
        return f"{float(value):.6f}"
    if name == "is_empty_response":
        return "Sim" if float(value) >= 1 else "Não"
    if name == "json_validity":
        return "Válido" if float(value) >= 1 else "Inválido"
    if name == "safety_suite_pass":
        return "Passou" if float(value) >= 1 else "Falhou"
    if name == "critical_divergence":
        return "Sem divergência" if float(value) >= 1 else "Com divergência"
    if name in {"correctness", "completeness", "clarity", "helpfulness", "safety", "instruction_following"}:
        return f"{float(value):.1f}"
    return f"{float(value):.4f}"


def scenario_label(value: str) -> str:
    return SCENARIO_LABELS.get(value, value)


def severity_label(value: str) -> str:
    return SEVERITY_LABELS.get(value, value)


def status_label(value: str) -> str:
    return STATUS_LABELS.get(value, value)


def preset_label(value: str) -> str:
    return PRESET_LABELS.get(value, value)


def rubric_label(value: str) -> str:
    return RUBRIC_LABELS.get(value, value)
