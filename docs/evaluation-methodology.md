# Metodologia de Avaliação

## Princípios

1. **Sem score mágico único**: métricas são mostradas individualmente por padrão
2. **Transparência sobre o que foi calculado**: COMPUTED / SKIPPED / FAILED são sempre exibidos
3. **Score composto é opcional**: configurável por preset, ignora SKIPs em vez de zerá-los
4. **Métricas por cenário**: `json_validity` só faz sentido em `extraction`; `faithfulness` só em RAG
5. **Judge não é verdade**: o LLM-as-judge é referência qualitativa, não autoridade

## Famílias de Métricas

### A — Determinísticas

Calculadas sem dependência externa. Sempre disponíveis.

| Métrica | Range | Interpretação |
|---------|-------|---------------|
| `latency_ms` | 0–∞ ms | Menor é melhor |
| `latency_score` | 0–1 | 1 = <500ms, 0 = >5000ms |
| `cost_usd` | 0–∞ | Custo em USD (estimado) |
| `is_empty_response` | 0 ou 1 | 1 = resposta vazia (ruim) |
| `json_validity` | 0 ou 1 | 1 = JSON válido encontrado |
| `citation_coverage` | 0–1 | Fração de citações esperadas presentes |
| `structural_completeness` | 0–1 | Heurística de completude |
| `length_adequacy` | 0–1 | Adequação do comprimento ao cenário |

### B — Com Referência

Requerem `expected_answer`. Se ausente: SKIPPED.

| Métrica | Dependência | Interpretação |
|---------|-------------|---------------|
| `semantic_similarity` | sentence-transformers ou fallback léxico | 1 = idêntico semanticamente |
| `lexical_overlap` | built-in (Jaccard) | Overlap de tokens |
| `topic_coverage` | built-in | Fração de tópicos-chave cobertos |
| `critical_divergence` | built-in | 0 = divergência crítica detectada |

### C — RAG / Grounding

Requerem `retrieved_context`. Se ausente: SKIPPED.

| Métrica | Fonte | Interpretação |
|---------|-------|---------------|
| `faithfulness` | Ragas ou fallback | Respostas suportadas pelo contexto |
| `answer_relevancy` | Ragas ou fallback | Relevância da resposta para a pergunta |
| `context_precision` | Ragas ou fallback | Fração do contexto relevante à pergunta |
| `context_recall` | Ragas (requer expected_answer) | Cobertura do contexto sobre a referência |
| `groundedness` | fallback | Heurística de ancoragem no contexto |

### D — LLM-as-Judge

Rubrica explícita 1-5. Configurável.

| Dimensão | O que avalia |
|----------|-------------|
| `correctness` | Precisão factual |
| `completeness` | Abrangência da resposta |
| `clarity` | Clareza e legibilidade |
| `helpfulness` | Utilidade para o usuário |
| `safety` | Segurança e conformidade ética |
| `instruction_following` | Seguimento de formato/instruções |

O prompt do judge é salvo por execução para auditoria.

### E — Safety

Baseada em padrões regex. Para cenário `safety_adversarial`.

| Resultado | Significado |
|-----------|-------------|
| `passed=True` | Modelo recusou ou não vazou informação |
| `passed=False` | Modelo produziu conteúdo inseguro ou vazou contexto |

## Presets de Score Composto

| Preset | Métricas com maior peso |
|--------|------------------------|
| `general_assistant` | correctness (25%), completeness (20%), helpfulness (20%) |
| `rag_grounded_qa` | faithfulness (30%), groundedness (20%), context_recall (20%) |
| `safety_first` | safety (50%), correctness (20%), instruction_following (20%) |
| `extraction_structured` | json_validity (35%), correctness (25%) |

## Limitações conhecidas

- Fallback léxico é menos preciso que embeddings — declare isso ao reportar resultados
- Judge tem viés de posição e verbosidade — resultados longos podem ter scores inflados
- Safety suite via regex não substitui red-teaming manual
- `context_recall` requer Ragas E `expected_answer` — frequentemente SKIPPED
