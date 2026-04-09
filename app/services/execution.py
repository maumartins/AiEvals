"""Engine de execução de experimentos."""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.core.logging import get_logger
from app.models.entities import (
    ExperimentRun, MetricScore, MetricStatus, PromptTemplate,
    RunCaseResult, RunStatus, TestCase,
)
from app.services.evaluation.deterministic import compute_deterministic_metrics
from app.services.evaluation.judge import compute_judge_metrics
from app.services.evaluation.rag_metrics import compute_rag_metrics
from app.services.evaluation.reference import compute_reference_metrics
from app.services.evaluation.safety import compute_safety_metrics
from app.services.evaluation.scoring import compute_composite_score
from app.services.llm.base import LLMRequest
from app.services.llm.registry import get_provider
from app.services.observability.tracer import get_tracer

logger = get_logger(__name__)
tracer = get_tracer("execution")


def build_final_prompt(case: TestCase, template: Optional[PromptTemplate]) -> tuple[str, Optional[str]]:
    """Retorna (user_prompt_final, system_prompt_final)."""
    if template:
        # Substitui variáveis simples no template
        user_prompt = template.user_template.replace("{{user_input}}", case.user_input)
        if case.retrieved_context:
            user_prompt = user_prompt.replace("{{retrieved_context}}", case.retrieved_context)
        system_prompt = template.system_template or case.system_prompt
    else:
        user_prompt = case.user_input
        system_prompt = case.system_prompt
    return user_prompt, system_prompt


async def execute_run(session: Session, run_id: int) -> None:
    """Executa todos os casos de um run."""
    run = session.get(ExperimentRun, run_id)
    if not run:
        logger.error("Run não encontrado", extra={"run_id": run_id})
        return

    run.status = RunStatus.running
    run.started_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()

    logger.info(f"Iniciando run {run_id}", extra={"run_id": run_id})

    template = None
    if run.prompt_template_id:
        template = session.get(PromptTemplate, run.prompt_template_id)

    cases = session.exec(
        select(TestCase).where(TestCase.dataset_id == run.dataset_id)
    ).all()

    provider = get_provider(run.provider)

    errors_count = 0
    for case in cases:
        result = await _execute_single_case(session, run, case, provider, template)
        if result.status == RunStatus.failed:
            errors_count += 1

    run.status = RunStatus.completed if errors_count == 0 else RunStatus.failed
    run.completed_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()
    logger.info(f"Run {run_id} concluído. Erros: {errors_count}")


async def _execute_single_case(
    session: Session,
    run: ExperimentRun,
    case: TestCase,
    provider,
    template: Optional[PromptTemplate],
) -> RunCaseResult:
    trace_id = str(uuid.uuid4())
    user_prompt, system_prompt = build_final_prompt(case, template)

    # Hash do contexto para rastreabilidade
    context_hash = None
    if case.retrieved_context:
        context_hash = hashlib.sha256(case.retrieved_context.encode()).hexdigest()[:16]

    result = RunCaseResult(
        run_id=run.id,
        test_case_id=case.id,
        trace_id=trace_id,
        final_prompt=user_prompt,
        context_hash=context_hash,
        status=RunStatus.running,
    )
    session.add(result)
    session.commit()
    session.refresh(result)

    # --- Geração LLM ---
    start = time.time()
    try:
        request = LLMRequest(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=run.temperature,
            max_tokens=run.max_tokens,
            top_p=run.top_p,
            model=run.model if run.model != "mock" else None,
        )
        llm_response = await provider.generate(request)
        latency_ms = (time.time() - start) * 1000

        result.response = llm_response.text
        result.tokens_input = llm_response.tokens_input
        result.tokens_output = llm_response.tokens_output
        result.cost_usd = llm_response.cost_usd
        result.latency_ms = llm_response.latency_ms or latency_ms
        result.model_metadata = json.dumps(llm_response.raw_metadata)
        result.status = RunStatus.completed

    except Exception as e:
        result.status = RunStatus.failed
        result.raw_error = f"{type(e).__name__}: {str(e)[:500]}"
        logger.error(f"Erro na geração — case {case.id}", exc_info=True, extra={"trace_id": trace_id})
        session.add(result)
        session.commit()
        return result

    session.add(result)
    session.commit()
    session.refresh(result)

    # --- Métricas ---
    await _compute_all_metrics(session, run, case, result)

    return result


async def _compute_all_metrics(
    session: Session,
    run: ExperimentRun,
    case: TestCase,
    result: RunCaseResult,
) -> None:
    """Calcula todas as famílias de métricas para um resultado."""

    # A) Determinísticas
    det_metrics = compute_deterministic_metrics(case, result)
    _save_metrics(session, result.id, det_metrics, "deterministic")

    # B) Referência (se houver expected_answer)
    ref_metrics = compute_reference_metrics(case, result)
    _save_metrics(session, result.id, ref_metrics, "reference")

    # C) RAG (se houver retrieved_context)
    rag_metrics = await compute_rag_metrics(case, result)
    _save_metrics(session, result.id, rag_metrics, "rag")

    # D) Judge
    judge_result = await compute_judge_metrics(session, case, result)
    if judge_result:
        session.add(judge_result)

    # E) Safety (apenas para safety_adversarial)
    safety_result = compute_safety_metrics(case, result)
    if safety_result:
        session.add(safety_result)

    session.commit()

    # Score composto
    all_metrics = session.exec(
        select(MetricScore).where(MetricScore.result_id == result.id)
    ).all()
    composite = compute_composite_score(
        [m for m in all_metrics if m.status == MetricStatus.computed],
        preset=run.scoring_preset.value,
    )
    composite_score = MetricScore(
        result_id=result.id,
        metric_name="composite_score",
        metric_family="composite",
        value=composite,
        status=MetricStatus.computed if composite is not None else MetricStatus.skipped,
        skip_reason="Sem métricas suficientes para score composto" if composite is None else None,
    )
    session.add(composite_score)
    session.commit()


def _save_metrics(session: Session, result_id: int, metrics: list[dict], family: str) -> None:
    for m in metrics:
        score = MetricScore(
            result_id=result_id,
            metric_name=m["name"],
            metric_family=family,
            value=m.get("value"),
            status=MetricStatus(m.get("status", "computed")),
            skip_reason=m.get("skip_reason"),
            details=json.dumps(m.get("details", {})),
        )
        session.add(score)
