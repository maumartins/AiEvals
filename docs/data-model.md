# Modelo de Dados

## Entidades

### Dataset
Agrupa casos de teste por tema ou objetivo.
- `id`, `name`, `description`, `category`, `created_at`

### TestCase
Caso individual de avaliação.
- `dataset_id` → Dataset
- `user_input` (obrigatório)
- `system_prompt` (opcional)
- `expected_answer` (habilita métricas de referência)
- `retrieved_context` (habilita métricas RAG)
- `reference_context` (contexto de referência para julgamento)
- `expected_citations` (JSON array de strings)
- `metadata_json` (JSON livre)
- `severity`: low | medium | high
- `scenario_type`: general_qa | rag_qa | summarization | extraction | classification | safety_adversarial

### PromptTemplate
Template reutilizável com variáveis `{{user_input}}`, `{{retrieved_context}}`.
- `name`, `version`, `system_template`, `user_template`

### ExperimentRun
Uma execução de dataset contra um modelo com configuração específica.
- `dataset_id`, `prompt_template_id`
- `provider`, `model`, `temperature`, `max_tokens`, `top_p`
- `scoring_preset`: general_assistant | rag_grounded_qa | safety_first | extraction_structured
- `status`: pending | running | completed | failed

### RunCaseResult
Resultado de um caso dentro de um run.
- `run_id`, `test_case_id`
- `trace_id` (UUID único por caso)
- `final_prompt`, `response`
- `tokens_input`, `tokens_output`, `cost_usd`, `latency_ms`
- `context_hash` (SHA256 truncado do retrieved_context)
- `raw_error` (sanitizado, sem stacktrace)

### MetricScore
Uma métrica calculada para um resultado.
- `result_id`, `metric_name`, `metric_family`
- `value` (float ou null se SKIPPED/FAILED)
- `status`: computed | skipped | failed
- `skip_reason` (explicação quando SKIPPED)
- `details` (JSON com detalhes extras)

### JudgeResult
Avaliação LLM-as-judge para um resultado.
- `result_id`, `judge_provider`, `judge_model`
- `judge_prompt` (auditável)
- `correctness`, `completeness`, `clarity`, `helpfulness`, `safety`, `instruction_following` (1-5)
- `rationale` (resumo do julgamento)

### SafetyResult
Resultado de avaliação de segurança.
- `result_id`, `attack_type`, `passed`, `explanation`, `severity`

### AppSetting
Configurações dinâmicas da aplicação (key-value).

## Diagrama simplificado

```
Dataset ──< TestCase ──< RunCaseResult >── ExperimentRun
                              │
                    ┌─────────┼──────────┐
                    ▼         ▼          ▼
              MetricScore  JudgeResult  SafetyResult
```
