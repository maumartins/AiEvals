# Modelo de Dados

## Entidades

### Dataset

Agrupa casos de teste.

- `id`
- `name`
- `description`
- `category`
- `created_at`

### TestCase

Representa um caso individual.

- `id`
- `dataset_id`
- `name`
- `category`
- `tags`
- `user_input`
- `system_prompt`
- `expected_answer`
- `retrieved_context`
- `reference_context`
- `expected_citations`
- `metadata_json`
- `severity`
- `scenario_type`
- `created_at`

`metadata_json` suporta regras como:

- `required_keywords`
- `forbidden_keywords`
- `regex_must_match`
- `regex_must_not_match`
- `response_format`
- `json_schema_required`

### PromptTemplate

- `id`
- `name`
- `version`
- `system_template`
- `user_template`
- `description`
- `created_at`

Variaveis suportadas no MVP:

- `{{user_input}}`
- `{{retrieved_context}}`
- `{{reference_context}}`
- `{{expected_answer}}`
- `{{expected_citations}}`

### ExperimentRun

Configura uma execucao sobre um dataset.

- `id`
- `name`
- `dataset_id`
- `prompt_template_id`
- `provider`
- `model`
- `temperature`
- `max_tokens`
- `top_p`
- `rubric_preset`
- `prompt_version`
- `scoring_preset`
- `enabled_metrics`
- `status`
- `error_message`
- `started_at`
- `completed_at`
- `created_at`

### RunCaseResult

Resultado operacional e analitico por caso.

- `id`
- `run_id`
- `test_case_id`
- `trace_id`
- `final_prompt`
- `prompt_version`
- `response`
- `tokens_input`
- `tokens_output`
- `cost_usd`
- `latency_ms`
- `status`
- `raw_error`
- `model_metadata`
- `context_hash`
- `timestamp`

### MetricScore

Cada metrica e persistida separadamente.

- `id`
- `result_id`
- `metric_name`
- `metric_family`
- `value`
- `status`
- `skip_reason`
- `details`

### JudgeResult

- `id`
- `result_id`
- `judge_provider`
- `judge_model`
- `judge_prompt`
- `correctness`
- `completeness`
- `clarity`
- `helpfulness`
- `safety`
- `instruction_following`
- `rationale`
- `raw_response`
- `timestamp`

### SafetyResult

- `id`
- `result_id`
- `attack_type`
- `passed`
- `explanation`
- `severity`
- `timestamp`

### AppSetting

- `key`
- `value`
- `description`
- `updated_at`

## Relacoes

```text
Dataset 1 ── * TestCase
ExperimentRun 1 ── * RunCaseResult
TestCase 1 ── * RunCaseResult
RunCaseResult 1 ── * MetricScore
RunCaseResult 1 ── 1 JudgeResult
RunCaseResult 1 ── 1 SafetyResult
```

## Observacoes

- `trace_id` e rastreavel na UI e nos logs.
- `prompt_version` e salvo no run e no resultado por caso.
- `raw_error` e sanitizado.
- `enabled_metrics` controla familias de metricas, nao um framework generico de plugins.
