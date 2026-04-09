"""Engine de execucao de experimentos."""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.core.logging import get_logger, redact
from app.db.engine import engine as default_engine
from app.models.entities import (
    ExperimentRun,
    JudgeResult,
    MetricScore,
    MetricStatus,
    PromptTemplate,
    RunCaseResult,
    RunStatus,
    SafetyResult,
    TestCase,
)
from app.services.evaluation.deterministic import compute_deterministic_metrics
from app.services.evaluation.judge import compute_judge_metrics, judge_result_to_metrics
from app.services.evaluation.rag_metrics import compute_rag_metrics
from app.services.evaluation.reference import compute_reference_metrics
from app.services.evaluation.safety import compute_safety_metrics
from app.services.evaluation.scoring import compute_composite_score
from app.services.llm.base import LLMRequest
from app.services.llm.registry import get_provider
from app.services.observability.tracer import current_trace_id, get_tracer

logger = get_logger(__name__)
tracer = get_tracer("execution")

DEFAULT_METRIC_FAMILIES = ["deterministic", "reference", "rag", "judge", "safety"]
FAMILY_METRIC_NAMES = {
    "deterministic": [
        "latency_ms",
        "latency_score",
        "cost_usd",
        "response_length_chars",
        "is_empty_response",
        "json_validity",
        "citation_coverage",
        "structural_completeness",
        "length_adequacy",
        "prompt_token_count",
        "response_token_count",
        "total_token_count",
        "keyword_rule_adherence",
        "regex_rule_adherence",
    ],
    "reference": [
        "semantic_similarity",
        "lexical_overlap",
        "factual_correctness",
        "topic_coverage",
        "critical_divergence",
    ],
    "rag": [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "groundedness",
    ],
    "judge": [
        "correctness",
        "completeness",
        "clarity",
        "helpfulness",
        "safety",
        "instruction_following",
    ],
    "safety": [
        "safety_suite_pass",
    ],
}


def build_final_prompt(
    case: TestCase,
    template: Optional[PromptTemplate],
) -> tuple[str, Optional[str], str]:
    """Retorna (user_prompt_final, system_prompt_final, prompt_version)."""
    variables = {
        "user_input": case.user_input,
        "retrieved_context": case.retrieved_context or "",
        "reference_context": case.reference_context or "",
        "expected_answer": case.expected_answer or "",
        "expected_citations": case.expected_citations or "",
    }

    if template:
        user_prompt = template.user_template
        system_prompt = template.system_template or case.system_prompt
        for key, value in variables.items():
            user_prompt = user_prompt.replace(f"{{{{{key}}}}}", value)
            if system_prompt:
                system_prompt = system_prompt.replace(f"{{{{{key}}}}}", value)
        return user_prompt, system_prompt, template.version or "template"

    return case.user_input, case.system_prompt, "ad-hoc"


async def execute_run(run_id: int, engine_override: Engine | None = None) -> None:
    """Executa um run abrindo sua propria Session."""
    active_engine = engine_override or default_engine
    with Session(active_engine) as session:
        await _execute_run_with_session(session, run_id)


async def reevaluate_run(run_id: int, engine_override: Engine | None = None) -> None:
    """Reexecuta apenas judge, segurança e score composto para um run já concluído."""
    active_engine = engine_override or default_engine
    with Session(active_engine) as session:
        run = session.get(ExperimentRun, run_id)
        if not run:
            return

        results = session.exec(select(RunCaseResult).where(RunCaseResult.run_id == run_id)).all()
        for result in results:
            if result.status != RunStatus.completed:
                continue

            case = session.get(TestCase, result.test_case_id)
            if not case:
                continue

            _delete_auxiliary_artifacts(session, result.id)
            await _compute_auxiliary_metrics(session, run, case, result)


async def _execute_run_with_session(session: Session, run_id: int) -> None:
    run = session.get(ExperimentRun, run_id)
    if not run:
        logger.error("Run nao encontrado", extra={"run_id": run_id})
        return

    run.status = RunStatus.running
    run.started_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()

    template = session.get(PromptTemplate, run.prompt_template_id) if run.prompt_template_id else None
    run.prompt_version = template.version if template and template.version else "ad-hoc"
    session.add(run)
    session.commit()

    cases = session.exec(select(TestCase).where(TestCase.dataset_id == run.dataset_id)).all()
    provider = get_provider(run.provider)
    errors_count = 0

    with tracer.start_as_current_span(
        "run_execution",
        attributes={
            "run.id": run.id or 0,
            "run.provider": run.provider,
            "run.model": run.model,
            "run.prompt_version": run.prompt_version,
            "run.dataset_id": run.dataset_id,
        },
    ):
        logger.info(
            "Iniciando run",
            extra={
                "run_id": run.id,
                "trace_id": current_trace_id(),
            },
        )

        for case in cases:
            result = await _execute_single_case(session, run, case, provider, template)
            if result.status == RunStatus.failed:
                errors_count += 1

    run.status = RunStatus.completed if errors_count == 0 else RunStatus.failed
    run.completed_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()
    logger.info(
        "Run concluido",
        extra={
            "run_id": run.id,
            "trace_id": current_trace_id(),
        },
    )


async def _execute_single_case(
    session: Session,
    run: ExperimentRun,
    case: TestCase,
    provider,
    template: Optional[PromptTemplate],
) -> RunCaseResult:
    user_prompt, system_prompt, prompt_version = build_final_prompt(case, template)
    context_hash = None
    if case.retrieved_context:
        context_hash = hashlib.sha256(case.retrieved_context.encode()).hexdigest()[:16]

    with tracer.start_as_current_span(
        "case_execution",
        attributes={
            "run.id": run.id or 0,
            "case.id": case.id or 0,
            "case.scenario_type": case.scenario_type.value,
            "case.severity": case.severity.value,
        },
    ) as case_span:
        trace_id = current_trace_id()
        result = RunCaseResult(
            run_id=run.id,
            test_case_id=case.id,
            trace_id=trace_id or str(case_span.get_span_context().trace_id),
            final_prompt=user_prompt,
            prompt_version=prompt_version,
            context_hash=context_hash,
            status=RunStatus.running,
        )
        session.add(result)
        session.commit()
        session.refresh(result)

        start = time.time()
        try:
            with tracer.start_as_current_span(
                "generation",
                attributes={
                    "llm.provider": run.provider,
                    "llm.model": run.model,
                    "prompt.version": prompt_version,
                },
            ):
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
        except Exception as exc:
            result.status = RunStatus.failed
            result.raw_error = redact(f"{type(exc).__name__}: {str(exc)[:500]}")
            logger.error(
                "Erro na geracao",
                exc_info=True,
                extra={"trace_id": trace_id, "run_id": run.id},
            )
            session.add(result)
            session.commit()
            return result

        session.add(result)
        session.commit()
        session.refresh(result)

        await _compute_all_metrics(session, run, case, result)
        return result


async def _compute_all_metrics(
    session: Session,
    run: ExperimentRun,
    case: TestCase,
    result: RunCaseResult,
) -> None:
    enabled_families = _enabled_metric_families(run)

    family_specs = [
        ("deterministic", "deterministic_metrics", compute_deterministic_metrics, False),
        ("reference", "reference_metrics", compute_reference_metrics, False),
        ("rag", "rag_metrics", compute_rag_metrics, True),
    ]

    for family_name, span_name, fn, is_async in family_specs:
        if family_name not in enabled_families:
            _save_metrics(
                session,
                result.id,
                _disabled_family_metrics(family_name),
                family_name,
            )
            continue

        try:
            with tracer.start_as_current_span(span_name):
                metrics = await fn(case, result) if is_async else fn(case, result)
            _save_metrics(session, result.id, metrics, family_name)
        except Exception as exc:
            logger.warning(
                "Falha ao calcular familia de metricas",
                extra={"trace_id": result.trace_id, "run_id": run.id},
            )
            _save_metrics(
                session,
                result.id,
                _failed_family_metrics(family_name, str(exc)),
                family_name,
            )

    await _compute_auxiliary_metrics(session, run, case, result, enabled_families=enabled_families)


def _enabled_metric_families(run: ExperimentRun) -> set[str]:
    configured = run.get_enabled_metrics()
    if not configured:
        return set(DEFAULT_METRIC_FAMILIES)
    return {item for item in configured if item in FAMILY_METRIC_NAMES}


async def _compute_auxiliary_metrics(
    session: Session,
    run: ExperimentRun,
    case: TestCase,
    result: RunCaseResult,
    enabled_families: set[str] | None = None,
) -> None:
    enabled = enabled_families or _enabled_metric_families(run)

    if "judge" in enabled:
        try:
            with tracer.start_as_current_span("judge_evaluation"):
                judge_result = await compute_judge_metrics(
                    case,
                    result,
                    rubric_preset=run.rubric_preset,
                )
            if judge_result:
                session.add(judge_result)
                session.commit()
                session.refresh(judge_result)
                _save_metrics(session, result.id, judge_result_to_metrics(judge_result), "judge")
        except Exception as exc:
            _save_metrics(session, result.id, _failed_family_metrics("judge", str(exc)), "judge")
    else:
        _save_metrics(session, result.id, _disabled_family_metrics("judge"), "judge")

    if "safety" in enabled:
        try:
            with tracer.start_as_current_span("safety_evaluation"):
                safety_result = compute_safety_metrics(case, result)
            if safety_result:
                session.add(safety_result)
                session.commit()
                session.refresh(safety_result)
                _save_metrics(
                    session,
                    result.id,
                    [
                        {
                            "name": "safety_suite_pass",
                            "value": 1.0 if safety_result.passed else 0.0,
                            "status": "computed",
                            "details": {"attack_type": safety_result.attack_type},
                        }
                    ],
                    "safety",
                )
            else:
                _save_metrics(
                    session,
                    result.id,
                    [
                        {
                            "name": "safety_suite_pass",
                            "value": None,
                            "status": "skipped",
                            "skip_reason": "Cenário não é do tipo safety_adversarial",
                            "details": {},
                        }
                    ],
                    "safety",
                )
        except Exception as exc:
            _save_metrics(session, result.id, _failed_family_metrics("safety", str(exc)), "safety")
    else:
        _save_metrics(session, result.id, _disabled_family_metrics("safety"), "safety")

    _recompute_composite_score(session, run, result.id)


def _recompute_composite_score(session: Session, run: ExperimentRun, result_id: int) -> None:
    existing = session.exec(
        select(MetricScore).where(
            MetricScore.result_id == result_id,
            MetricScore.metric_family == "composite",
        )
    ).all()
    for metric in existing:
        session.delete(metric)
    session.commit()

    all_metrics = session.exec(select(MetricScore).where(MetricScore.result_id == result_id)).all()
    composite = compute_composite_score(
        [metric for metric in all_metrics if metric.status == MetricStatus.computed],
        preset=run.scoring_preset.value,
    )
    session.add(
        MetricScore(
            result_id=result_id,
            metric_name="composite_score",
            metric_family="composite",
            value=composite,
            status=MetricStatus.computed if composite is not None else MetricStatus.skipped,
            skip_reason="Sem métricas suficientes para score composto" if composite is None else None,
            details=json.dumps({"preset": run.scoring_preset.value}),
        )
    )
    session.commit()


def _delete_auxiliary_artifacts(session: Session, result_id: int) -> None:
    judge_scores = session.exec(
        select(MetricScore).where(
            MetricScore.result_id == result_id,
            MetricScore.metric_family.in_(["judge", "safety", "composite"]),
        )
    ).all()
    for metric in judge_scores:
        session.delete(metric)

    judge_result = session.exec(select(JudgeResult).where(JudgeResult.result_id == result_id)).first()
    if judge_result:
        session.delete(judge_result)

    safety_result = session.exec(select(SafetyResult).where(SafetyResult.result_id == result_id)).first()
    if safety_result:
        session.delete(safety_result)

    session.commit()


def _disabled_family_metrics(family_name: str) -> list[dict]:
    return [
        {
            "name": metric_name,
            "value": None,
            "status": "skipped",
            "skip_reason": "Familia de metricas desabilitada nesta execucao",
            "details": {},
        }
        for metric_name in FAMILY_METRIC_NAMES[family_name]
    ]


def _failed_family_metrics(family_name: str, error_message: str) -> list[dict]:
    return [
        {
            "name": metric_name,
            "value": None,
            "status": "failed",
            "skip_reason": redact(error_message[:500]),
            "details": {},
        }
        for metric_name in FAMILY_METRIC_NAMES[family_name]
    ]


def _save_metrics(
    session: Session,
    result_id: int,
    metrics: list[dict[str, Any]],
    family: str,
) -> None:
    for metric in metrics:
        session.add(
            MetricScore(
                result_id=result_id,
                metric_name=metric["name"],
                metric_family=family,
                value=metric.get("value"),
                status=MetricStatus(metric.get("status", "computed")),
                skip_reason=metric.get("skip_reason"),
                details=json.dumps(metric.get("details", {})),
            )
        )
    session.commit()
