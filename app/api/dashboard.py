"""Rota do dashboard principal."""

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, func, select

from app.db.engine import get_session
from app.models.entities import Dataset, ExperimentRun, MetricScore, RunCaseResult, RunStatus, TestCase
from app.templates.renderer import render

router = APIRouter(tags=["dashboard"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: SessionDep):
    # Contagens gerais
    total_datasets = len(session.exec(select(Dataset)).all())
    total_cases = len(session.exec(select(TestCase)).all())
    total_runs = len(session.exec(select(ExperimentRun)).all())

    runs = session.exec(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())).all()
    all_results = session.exec(select(RunCaseResult)).all()

    completed_runs = [r for r in runs if r.status == RunStatus.completed]
    failed_runs = [r for r in runs if r.status == RunStatus.failed]

    # Latência e custo médios
    latencies = [r.latency_ms for r in all_results if r.latency_ms]
    costs = [r.cost_usd for r in all_results if r.cost_usd is not None]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else None
    avg_cost = round(sum(costs) / len(costs), 6) if costs else None

    # Métricas médias por modelo
    model_metrics: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        results = session.exec(select(RunCaseResult).where(RunCaseResult.run_id == run.id)).all()
        for result in results:
            metrics = session.exec(select(MetricScore).where(MetricScore.result_id == result.id)).all()
            for m in metrics:
                if m.value is not None and m.metric_name == "composite_score":
                    model_metrics[run.model][m.metric_name].append(m.value)

    model_summary = {
        model: {
            name: round(sum(vals) / len(vals), 4)
            for name, vals in metric_dict.items()
        }
        for model, metric_dict in model_metrics.items()
    }

    prompt_versions: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        run_results = session.exec(select(RunCaseResult).where(RunCaseResult.run_id == run.id)).all()
        for result in run_results:
            composite = session.exec(
                select(MetricScore).where(
                    MetricScore.result_id == result.id,
                    MetricScore.metric_name == "composite_score",
                )
            ).first()
            if composite and composite.value is not None:
                prompt_versions[result.prompt_version or run.prompt_version or "ad-hoc"].append(composite.value)

    prompt_version_summary = {
        prompt_version: round(sum(values) / len(values), 4)
        for prompt_version, values in prompt_versions.items()
    }

    recent_runs = runs[:10]
    for run in recent_runs:
        run._dataset = session.get(Dataset, run.dataset_id)

    return render(request, "dashboard.html", {
        "total_datasets": total_datasets,
        "total_cases": total_cases,
        "total_runs": total_runs,
        "completed_runs": len(completed_runs),
        "failed_runs": len(failed_runs),
        "avg_latency_ms": avg_latency,
        "avg_cost_usd": avg_cost,
        "model_summary": model_summary,
        "prompt_version_summary": prompt_version_summary,
        "recent_runs": recent_runs,
    })
