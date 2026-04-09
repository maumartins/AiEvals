"""Rota da suíte safety."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db.engine import get_session
from app.models.entities import Dataset, ExperimentRun, RunCaseResult, SafetyResult, ScenarioType, ScoringPreset
from app.services.evaluation.safety import get_safety_test_cases
from app.services.execution import execute_run
from app.services import datasets as dataset_svc
from app.templates.renderer import render

router = APIRouter(prefix="/safety", tags=["safety"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def safety_dashboard(request: Request, session: SessionDep):
    safety_results = session.exec(select(SafetyResult)).all()
    # Busca resultados enriquecidos
    enriched = []
    for sr in safety_results:
        result = session.get(RunCaseResult, sr.result_id)
        if result:
            run = session.get(ExperimentRun, result.run_id)
            enriched.append({
                "safety": sr,
                "result": result,
                "run": run,
            })
    predefined_cases = get_safety_test_cases()
    return render(request, "safety/dashboard.html", {
        "results": enriched,
        "predefined_cases": predefined_cases,
    })


@router.post("/run-suite")
async def run_safety_suite(
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    provider: str = Form("mock"),
    model: str = Form("mock"),
):
    """Cria um dataset de safety e roda automaticamente."""
    # Cria dataset temporário de safety
    dataset = dataset_svc.create_dataset(
        session,
        name="Safety Suite Auto",
        description="Suite adversarial automática",
        category="safety",
    )

    for tc in get_safety_test_cases():
        dataset_svc.create_case(session, dataset.id, {
            "name": tc["name"],
            "user_input": tc["user_input"],
            "severity": tc["severity"],
            "scenario_type": "safety_adversarial",
            "category": "safety",
        })

    run = ExperimentRun(
        name=f"Safety Suite — {provider}/{model}",
        dataset_id=dataset.id,
        provider=provider,
        model=model,
        scoring_preset=ScoringPreset.safety_first,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    background_tasks.add_task(execute_run, session, run.id)
    return RedirectResponse(f"/runs/{run.id}", status_code=303)
