"""Rotas da suíte de segurança."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.db.engine import get_session
from app.models.entities import Dataset, ExperimentRun, RunCaseResult, SafetyResult, ScenarioType, ScoringPreset, Severity, TestCase
from app.services import datasets as dataset_svc
from app.services.execution import execute_run
from app.services.llm.registry import AVAILABLE_PROVIDERS
from app.templates.renderer import render

router = APIRouter(prefix="/safety", tags=["safety"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def safety_dashboard(request: Request, session: SessionDep):
    safety_results = session.exec(select(SafetyResult).order_by(SafetyResult.timestamp.desc())).all()
    safety_cases = dataset_svc.list_cases_by_scenario(session, ScenarioType.safety_adversarial)
    safety_dataset_ids = sorted({case.dataset_id for case in safety_cases})
    safety_datasets = [session.get(Dataset, dataset_id) for dataset_id in safety_dataset_ids if session.get(Dataset, dataset_id)]

    enriched_results = []
    for safety_result in safety_results:
        result = session.get(RunCaseResult, safety_result.result_id)
        if result:
            run = session.get(ExperimentRun, result.run_id)
            enriched_results.append(
                {
                    "safety": safety_result,
                    "result": result,
                    "run": run,
                    "test_case": session.get(TestCase, result.test_case_id),
                }
            )

    return render(
        request,
        "safety/dashboard.html",
        {
            "results": enriched_results,
            "safety_cases": safety_cases,
            "safety_datasets": safety_datasets,
            "providers": AVAILABLE_PROVIDERS,
            "severity_values": [severity.value for severity in Severity],
        },
    )


@router.post("/cases")
async def create_safety_case(
    session: SessionDep,
    name: str = Form(...),
    user_input: str = Form(...),
    dataset_id: str = Form(""),
    category: str = Form("custom"),
    severity: str = Form("medium"),
    expected_answer: str = Form(""),
    metadata_json: str = Form("{}"),
):
    dataset = session.get(Dataset, int(dataset_id)) if dataset_id else dataset_svc.ensure_safety_dataset(session)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset de segurança não encontrado")

    dataset_svc.create_case(
        session,
        dataset.id,
        {
            "name": name,
            "user_input": user_input,
            "category": category,
            "severity": severity,
            "expected_answer": expected_answer or None,
            "metadata_json": metadata_json or "{}",
            "scenario_type": ScenarioType.safety_adversarial.value,
            "tags": ["safety", "adversarial"],
        },
    )
    return RedirectResponse("/safety/", status_code=303)


@router.post("/cases/{case_id}/delete")
async def delete_safety_case(case_id: int, session: SessionDep):
    case = dataset_svc.get_case(session, case_id)
    if not case or case.scenario_type != ScenarioType.safety_adversarial:
        raise HTTPException(status_code=404, detail="Cenário de segurança não encontrado")
    dataset_svc.delete_case(session, case_id)
    return RedirectResponse("/safety/", status_code=303)


@router.post("/run-suite")
async def run_safety_suite(
    request: Request,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    provider: str = Form("mock"),
    model: str = Form("mock"),
    dataset_id: str = Form(""),
):
    """Executa um dataset de segurança existente."""
    dataset = session.get(Dataset, int(dataset_id)) if dataset_id else dataset_svc.ensure_safety_dataset(session)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset de segurança não encontrado")

    run = ExperimentRun(
        name=f"Suíte de Segurança — {provider}/{model}",
        dataset_id=dataset.id,
        provider=provider,
        model=model,
        rubric_preset="safety_first",
        scoring_preset=ScoringPreset.safety_first,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    background_tasks.add_task(execute_run, run.id, session.get_bind())
    return RedirectResponse(f"/runs/{run.id}", status_code=303)
