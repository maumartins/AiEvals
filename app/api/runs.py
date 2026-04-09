"""Rotas de experimentos (runs)."""

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db.engine import get_session
from app.models.entities import (
    Dataset, ExperimentRun, JudgeResult, MetricScore, PromptTemplate,
    RunCaseResult, RunStatus, ScoringPreset, TestCase,
)
from app.services.execution import execute_run
from app.services.llm.registry import AVAILABLE_PROVIDERS
from app.templates.renderer import render

router = APIRouter(prefix="/runs", tags=["runs"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def list_runs(request: Request, session: SessionDep):
    runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())).all()
    # Injeta dataset name em cada run
    for run in runs:
        run._dataset = session.get(Dataset, run.dataset_id)
    return render(request, "runs/list.html", {"runs": runs})


@router.get("/new", response_class=HTMLResponse)
async def new_run_form(request: Request, session: SessionDep):
    datasets = session.exec(select(Dataset)).all()
    templates = session.exec(select(PromptTemplate)).all()
    presets = [p.value for p in ScoringPreset]
    return render(request, "runs/new.html", {
        "datasets": datasets,
        "templates": templates,
        "providers": AVAILABLE_PROVIDERS,
        "presets": presets,
    })


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
    scoring_preset: str = Form("general_assistant"),
    prompt_template_id: str = Form(""),
):
    template_id = int(prompt_template_id) if prompt_template_id else None
    run = ExperimentRun(
        name=name or f"Run {provider}/{model}",
        dataset_id=dataset_id,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        scoring_preset=ScoringPreset(scoring_preset),
        prompt_template_id=template_id,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Executa em background
    background_tasks.add_task(execute_run, session, run.id)

    return RedirectResponse(f"/runs/{run.id}", status_code=303)


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
    from collections import defaultdict
    runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())).all()

    def get_run_summary(rid: int):
        r = session.get(ExperimentRun, rid)
        if not r:
            return None
        results = session.exec(select(RunCaseResult).where(RunCaseResult.run_id == rid)).all()
        all_metrics = []
        for res in results:
            ms = session.exec(select(MetricScore).where(MetricScore.result_id == res.id)).all()
            all_metrics.extend(ms)
        grouped = defaultdict(list)
        for m in all_metrics:
            if m.value is not None:
                grouped[m.metric_name].append(m.value)
        metric_avgs = {name: round(sum(vals) / len(vals), 4) for name, vals in grouped.items()}

        latencies = [res.latency_ms for res in results if res.latency_ms]
        costs = [res.cost_usd for res in results if res.cost_usd]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        avg_cost = sum(costs) / len(costs) if costs else 0.0

        return {
            "run": r,
            "total": len(results),
            "completed": len([res for res in results if res.status == RunStatus.completed]),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_cost_usd": round(avg_cost, 6),
            "metrics": metric_avgs,
        }

    comparison = {"a": get_run_summary(run_a), "b": get_run_summary(run_b)}
    return render(request, "runs/compare.html", {"runs": runs, "comparison": comparison})


@router.get("/{run_id}", response_class=HTMLResponse)
async def run_detail(request: Request, run_id: int, session: SessionDep):
    run = session.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")

    dataset = session.get(Dataset, run.dataset_id)
    results = session.exec(
        select(RunCaseResult).where(RunCaseResult.run_id == run_id)
    ).all()

    # Enriquece resultados com métricas e test case
    enriched = []
    for r in results:
        test_case = session.get(TestCase, r.test_case_id)
        metrics = session.exec(
            select(MetricScore).where(MetricScore.result_id == r.id)
        ).all()
        judge = session.exec(
            select(JudgeResult).where(JudgeResult.result_id == r.id)
        ).first()
        enriched.append({
            "result": r,
            "test_case": test_case,
            "metrics": metrics,
            "judge": judge,
        })

    return render(request, "runs/detail.html", {
        "run": run,
        "dataset": dataset,
        "results": enriched,
    })


@router.get("/{run_id}/status")
async def run_status(run_id: int, session: SessionDep):
    """Endpoint HTMX para polling de status."""
    run = session.get(ExperimentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    results_count = len(session.exec(
        select(RunCaseResult).where(RunCaseResult.run_id == run_id)
    ).all())
    return {"status": run.status.value, "results_count": results_count}


