"""Rotas de experimentos."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.core.presentation import metric_meta
from app.db.engine import get_session
from app.models.entities import (
    Dataset,
    ExperimentRun,
    JudgeResult,
    MetricScore,
    PromptTemplate,
    RunCaseResult,
    RunStatus,
    SafetyResult,
    ScoringPreset,
    TestCase,
)
from app.services.evaluation.judge import AVAILABLE_RUBRIC_PRESETS
from app.services.execution import DEFAULT_METRIC_FAMILIES, execute_run, reevaluate_run
from app.services.llm.registry import AVAILABLE_PROVIDERS
from app.templates.renderer import render

router = APIRouter(prefix="/runs", tags=["runs"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def list_runs(
    request: Request,
    session: SessionDep,
    dataset_id: int | None = Query(default=None),
    model: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    tag: str | None = Query(default=None),
):
    runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())).all()
    datasets = session.exec(select(Dataset).order_by(Dataset.name)).all()
    filtered_runs = []

    for run in runs:
        run._dataset = session.get(Dataset, run.dataset_id)
        if dataset_id and run.dataset_id != dataset_id:
            continue
        if model and model.lower() not in run.model.lower():
            continue
        if any([category, severity, tag]) and not _run_matches_case_filters(
            session,
            run.id,
            category=category,
            severity=severity,
            tag=tag,
        ):
            continue
        filtered_runs.append(run)

    return render(
        request,
        "runs/list.html",
        {
            "runs": filtered_runs,
            "datasets": datasets,
            "filters": {
                "dataset_id": dataset_id,
                "model": model or "",
                "category": category or "",
                "severity": severity or "",
                "tag": tag or "",
            },
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_run_form(request: Request, session: SessionDep):
    datasets = session.exec(select(Dataset)).all()
    templates = session.exec(select(PromptTemplate)).all()
    presets = [preset.value for preset in ScoringPreset]
    return render(
        request,
        "runs/new.html",
        {
            "datasets": datasets,
            "templates": templates,
            "providers": AVAILABLE_PROVIDERS,
            "presets": presets,
            "rubric_presets": AVAILABLE_RUBRIC_PRESETS,
            "metric_families": DEFAULT_METRIC_FAMILIES,
        },
    )


@router.post("/")
async def create_run(
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    name: str = Form(""),
    dataset_id: int = Form(...),
    provider: str = Form("mock"),
    model: str = Form("mock"),
    temperature: float = Form(0.0),
    max_tokens: int = Form(1024),
    top_p: float | None = Form(default=None),
    rubric_preset: str = Form("balanced"),
    scoring_preset: str = Form("general_assistant"),
    prompt_template_id: str = Form(""),
    enabled_metrics: list[str] = Form(default=[]),
):
    template = session.get(PromptTemplate, int(prompt_template_id)) if prompt_template_id else None
    run = ExperimentRun(
        name=name or f"Experimento {provider}/{model}",
        dataset_id=dataset_id,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        rubric_preset=rubric_preset,
        scoring_preset=ScoringPreset(scoring_preset),
        prompt_template_id=int(prompt_template_id) if prompt_template_id else None,
        prompt_version=template.version if template and template.version else "ad-hoc",
        enabled_metrics=json.dumps(enabled_metrics or DEFAULT_METRIC_FAMILIES),
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    background_tasks.add_task(execute_run, run.id, session.get_bind())
    return RedirectResponse(f"/runs/{run.id}", status_code=303)


@router.post("/{run_id}/reevaluate")
async def rerun_auxiliary_evaluations(run_id: int, background_tasks: BackgroundTasks, session: SessionDep):
    run = session.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Experimento não encontrado")
    background_tasks.add_task(reevaluate_run, run_id, session.get_bind())
    return RedirectResponse(f"/runs/{run_id}", status_code=303)


@router.get("/compare", response_class=HTMLResponse)
async def compare_form(request: Request, session: SessionDep):
    runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())).all()
    return render(request, "runs/compare.html", {"runs": runs, "comparison": None})


@router.post("/compare", response_class=HTMLResponse)
async def compare_runs(
    request: Request,
    session: SessionDep,
    run_a: int = Form(...),
    run_b: int = Form(...),
):
    runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())).all()
    comparison = {
        "a": _build_run_summary(session, run_a),
        "b": _build_run_summary(session, run_b),
    }
    comparison["case_rows"] = _build_case_rows(comparison["a"], comparison["b"])
    return render(request, "runs/compare.html", {"runs": runs, "comparison": comparison})


@router.get("/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: int, session: SessionDep):
    run = session.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Experimento não encontrado")

    dataset = session.get(Dataset, run.dataset_id)
    results = session.exec(select(RunCaseResult).where(RunCaseResult.run_id == run_id)).all()
    template = session.get(PromptTemplate, run.prompt_template_id) if run.prompt_template_id else None
    enriched = []
    judge_complete = 0
    safety_complete = 0
    safety_passed = 0

    for result in results:
        test_case = session.get(TestCase, result.test_case_id)
        metrics = session.exec(select(MetricScore).where(MetricScore.result_id == result.id)).all()
        metrics = sorted(metrics, key=lambda item: (item.metric_family, metric_meta(item.metric_name)["label"]))
        judge = session.exec(select(JudgeResult).where(JudgeResult.result_id == result.id)).first()
        safety = session.exec(select(SafetyResult).where(SafetyResult.result_id == result.id)).first()
        if judge and any(getattr(judge, field) is not None for field in [
            "correctness",
            "completeness",
            "clarity",
            "helpfulness",
            "safety",
            "instruction_following",
        ]):
            judge_complete += 1
        if safety:
            safety_complete += 1
            if safety.passed:
                safety_passed += 1
        enriched.append(
            {
                "result": result,
                "test_case": test_case,
                "metrics": metrics,
                "judge": judge,
                "safety": safety,
            }
        )

    return render(
        request,
        "runs/detail.html",
        {
            "run": run,
            "dataset": dataset,
            "template": template,
            "results": enriched,
            "enabled_metrics": run.get_enabled_metrics() or DEFAULT_METRIC_FAMILIES,
            "judge_complete": judge_complete,
            "safety_complete": safety_complete,
            "safety_passed": safety_passed,
        },
    )


@router.get("/{run_id}/status", response_class=HTMLResponse)
async def run_status(run_id: int, session: SessionDep):
    run = session.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Experimento não encontrado")
    results_count = len(session.exec(select(RunCaseResult).where(RunCaseResult.run_id == run_id)).all())
    return HTMLResponse(_status_badge_html(run_id, run.status, results_count))


def _run_matches_case_filters(
    session: Session,
    run_id: int,
    category: str | None,
    severity: str | None,
    tag: str | None,
) -> bool:
    results = session.exec(select(RunCaseResult).where(RunCaseResult.run_id == run_id)).all()
    if not results:
        return False

    for result in results:
        case = session.get(TestCase, result.test_case_id)
        if not case:
            continue
        if category and category.lower() not in (case.category or "").lower():
            continue
        if severity and case.severity.value != severity:
            continue
        if tag and tag.lower() not in [item.lower() for item in case.get_tags()]:
            continue
        return True
    return False


def _build_run_summary(session: Session, run_id: int) -> dict | None:
    run = session.get(ExperimentRun, run_id)
    if not run:
        return None

    results = session.exec(select(RunCaseResult).where(RunCaseResult.run_id == run_id)).all()
    all_metrics = []
    cases = {}
    safety_passed = 0
    safety_failed = 0

    for result in results:
        metrics = session.exec(select(MetricScore).where(MetricScore.result_id == result.id)).all()
        all_metrics.extend(metrics)
        case = session.get(TestCase, result.test_case_id)
        safety = session.exec(select(SafetyResult).where(SafetyResult.result_id == result.id)).first()
        if safety:
            if safety.passed:
                safety_passed += 1
            else:
                safety_failed += 1
        cases[result.test_case_id] = {"case": case, "result": result, "metrics": metrics, "safety": safety}

    grouped = defaultdict(list)
    for metric in all_metrics:
        if metric.value is not None:
            grouped[metric.metric_name].append(metric.value)

    metric_avgs = {
        metric_name: round(sum(values) / len(values), 4)
        for metric_name, values in grouped.items()
    }
    latencies = [result.latency_ms for result in results if result.latency_ms is not None]
    costs = [result.cost_usd for result in results if result.cost_usd is not None]

    return {
        "run": run,
        "total": len(results),
        "completed": len([result for result in results if result.status == RunStatus.completed]),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "avg_cost_usd": round(sum(costs) / len(costs), 6) if costs else 0.0,
        "metrics": metric_avgs,
        "cases": cases,
        "safety_passed": safety_passed,
        "safety_failed": safety_failed,
    }


def _build_case_rows(summary_a: dict | None, summary_b: dict | None) -> list[dict]:
    if not summary_a or not summary_b:
        return []

    case_ids = sorted(set(summary_a["cases"].keys()) | set(summary_b["cases"].keys()))
    rows = []
    for case_id in case_ids:
        left = summary_a["cases"].get(case_id)
        right = summary_b["cases"].get(case_id)
        case = left["case"] if left else right["case"]
        rows.append(
            {
                "name": case.name if case and case.name else f"Caso {case_id}",
                "scenario_type": case.scenario_type.value if case else "unknown",
                "a_composite": _metric_value(left, "composite_score"),
                "b_composite": _metric_value(right, "composite_score"),
                "a_latency": left["result"].latency_ms if left else None,
                "b_latency": right["result"].latency_ms if right else None,
                "a_tokens": _metric_value(left, "total_token_count"),
                "b_tokens": _metric_value(right, "total_token_count"),
                "a_safety": left["safety"].passed if left and left.get("safety") else None,
                "b_safety": right["safety"].passed if right and right.get("safety") else None,
            }
        )
    return rows


def _metric_value(case_payload: dict | None, metric_name: str) -> float | None:
    if not case_payload:
        return None
    for metric in case_payload["metrics"]:
        if metric.metric_name == metric_name:
            return metric.value
    return None


def _status_badge_html(run_id: int, status: RunStatus, results_count: int) -> str:
    if status == RunStatus.completed:
        # Força reload completo da página para exibir métricas geradas em background
        return (
            '<span class="badge-green text-base px-3 py-1">Concluído</span>'
            "<script>window.location.reload();</script>"
        )
    if status == RunStatus.failed:
        return (
            '<span class="badge-red text-base px-3 py-1">Falhou</span>'
            "<script>window.location.reload();</script>"
        )
    if status == RunStatus.running:
        return (
            f'<span class="badge-yellow text-base px-3 py-1" id="status-badge" '
            f'hx-get="/runs/{run_id}/status" hx-trigger="every 3s" hx-swap="outerHTML">'
            f'Em execução ({results_count})'
            "</span>"
        )
    return '<span class="badge-gray text-base px-3 py-1">Pendente</span>'
