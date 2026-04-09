# Metodologia de Avaliacao

## Principios

1. Sem score magico unico por padrao.
2. Metricas por cenario e por risco.
3. Transparencia sobre `COMPUTED`, `SKIPPED` e `FAILED`.
4. Judge model e referencia qualitativa, nao verdade absoluta.
5. Fallback explicito quando faltar dependencia ou contexto.

## Familias de metricas

### Deterministicas

Usadas para verificar atributos objetivos do output:

- latencia
- custo
- tamanho da resposta
- resposta vazia
- validade JSON
- presenca de citacoes
- completude estrutural
- adequacao de comprimento
- aderencia a regras de keyword
- aderencia a regex

### Com referencia

Requerem `expected_answer` e opcionalmente `reference_context`:

- similaridade semantica
- overlap lexical
- factual correctness aproximada
- topic coverage
- critical divergence

### RAG / grounding

Requerem `retrieved_context`:

- faithfulness
- answer_relevancy
- context_precision
- context_recall
- groundedness

Quando Ragas estiver instalado, o laboratorio usa Ragas. Sem Ragas, cai para fallback lexical e explicita isso em `details`.

### Judge

Rubricas 1-5:

- correctness
- completeness
- clarity
- helpfulness
- safety
- instruction_following

Rubric presets disponiveis:

- `balanced`
- `strict_grounded`
- `safety_first`
- `structured_output`

### Safety

Avalia cenarios adversariais como:

- prompt injection
- ignorar instrucoes
- extracao de system prompt
- bypass de policy
- refusal quality
- vazamento basico de email, telefone e API key

## Quando cada metrica faz sentido

### general_qa

- judge
- semantic_similarity
- factual_correctness
- topic_coverage

### rag_qa

- faithfulness
- groundedness
- context_precision
- context_recall
- judge com preset mais estrito

### extraction

- json_validity
- regex_rule_adherence
- keyword_rule_adherence
- instruction_following

### safety_adversarial

- safety_suite_pass
- judge safety
- explicacao adversarial por caso

## Composite score

O score composto:

- e calculado por preset
- ignora metricas `SKIPPED`
- usa apenas metricas presentes
- existe para comparacao, nao para substituicao de analise

Presets:

- `general_assistant`
- `rag_grounded_qa`
- `safety_first`
- `extraction_structured`

## Limitacoes

- Heuristicas lexicais nao equivalem a verificacao factual robusta.
- Judge LLM tende a sofrer vies por estilo, verbosity e alinhamento do proprio modelo.
- Safety via regex nao cobre todos os ataques indiretos.
- `context_recall` depende de formato de caso compativel.
