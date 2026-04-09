"""Rotas de datasets."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlmodel import Session

from app.db.engine import get_session
from app.models.entities import ScenarioType, Severity
from app.services import datasets as svc
from app.templates.renderer import render

router = APIRouter(prefix="/datasets", tags=["datasets"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def list_datasets(request: Request, session: SessionDep):
    items = svc.list_datasets(session)
    return render(request, "datasets/list.html", {"datasets": items})


@router.get("/new", response_class=HTMLResponse)
async def new_dataset_form(request: Request):
    return render(request, "datasets/new.html", {})


@router.post("/")
async def create_dataset(
    request: Request,
    session: SessionDep,
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form(""),
):
    dataset = svc.create_dataset(session, name=name, description=description, category=category)
    return RedirectResponse(f"/datasets/{dataset.id}", status_code=303)


@router.post("/{dataset_id}")
async def update_dataset(
    dataset_id: int,
    session: SessionDep,
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form(""),
):
    dataset = svc.update_dataset(session, dataset_id, name=name, description=description, category=category)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")
    return RedirectResponse(f"/datasets/{dataset_id}", status_code=303)


@router.get("/{dataset_id}", response_class=HTMLResponse)
async def dataset_detail(request: Request, dataset_id: int, session: SessionDep):
    dataset = svc.get_dataset(session, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")
    cases = svc.list_cases(session, dataset_id)
    return render(
        request,
        "datasets/detail.html",
        {
            "dataset": dataset,
            "cases": cases,
            "scenario_values": [scenario.value for scenario in ScenarioType],
            "severity_values": [severity.value for severity in Severity],
        },
    )


@router.get("/{dataset_id}/export")
async def export_dataset(
    dataset_id: int,
    session: SessionDep,
    format: str = Query(default="jsonl"),
):
    dataset = svc.get_dataset(session, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")

    if format == "csv":
        content = svc.export_dataset_csv(session, dataset_id)
        media_type = "text/csv; charset=utf-8"
        filename = f'{dataset.name.replace(" ", "_").lower()}.csv'
    else:
        content = svc.export_dataset_jsonl(session, dataset_id)
        media_type = "application/x-ndjson; charset=utf-8"
        filename = f'{dataset.name.replace(" ", "_").lower()}.jsonl'

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)


@router.get("/{dataset_id}/cases/{case_id}", response_class=HTMLResponse)
async def case_detail(request: Request, dataset_id: int, case_id: int, session: SessionDep):
    dataset = svc.get_dataset(session, dataset_id)
    case = svc.get_case(session, case_id)
    if not dataset or not case or case.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Caso de teste não encontrado")
    return render(
        request,
        "datasets/case_detail.html",
        {
            "dataset": dataset,
            "case": case,
            "scenario_values": [scenario.value for scenario in ScenarioType],
            "severity_values": [severity.value for severity in Severity],
        },
    )


@router.post("/{dataset_id}/cases")
async def add_case(
    request: Request,
    dataset_id: int,
    session: SessionDep,
    user_input: str = Form(...),
    name: str = Form(""),
    category: str = Form(""),
    tags: str = Form("[]"),
    system_prompt: str = Form(""),
    expected_answer: str = Form(""),
    retrieved_context: str = Form(""),
    reference_context: str = Form(""),
    expected_citations: str = Form(""),
    metadata_json: str = Form("{}"),
    severity: str = Form("low"),
    scenario_type: str = Form("general_qa"),
):
    data = {
        "user_input": user_input,
        "name": name,
        "category": category,
        "tags": tags,
        "system_prompt": system_prompt or None,
        "expected_answer": expected_answer or None,
        "retrieved_context": retrieved_context or None,
        "reference_context": reference_context or None,
        "expected_citations": expected_citations or None,
        "metadata_json": metadata_json or "{}",
        "severity": severity,
        "scenario_type": scenario_type,
    }
    svc.create_case(session, dataset_id, data)
    return RedirectResponse(f"/datasets/{dataset_id}", status_code=303)


@router.post("/{dataset_id}/cases/{case_id}")
async def update_case(
    dataset_id: int,
    case_id: int,
    session: SessionDep,
    user_input: str = Form(...),
    name: str = Form(""),
    category: str = Form(""),
    tags: str = Form("[]"),
    system_prompt: str = Form(""),
    expected_answer: str = Form(""),
    retrieved_context: str = Form(""),
    reference_context: str = Form(""),
    expected_citations: str = Form(""),
    metadata_json: str = Form("{}"),
    severity: str = Form("low"),
    scenario_type: str = Form("general_qa"),
):
    case = svc.get_case(session, case_id)
    if not case or case.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Caso de teste não encontrado")

    svc.update_case(
        session,
        case_id,
        {
            "user_input": user_input,
            "name": name,
            "category": category,
            "tags": tags,
            "system_prompt": system_prompt or None,
            "expected_answer": expected_answer or None,
            "retrieved_context": retrieved_context or None,
            "reference_context": reference_context or None,
            "expected_citations": expected_citations or None,
            "metadata_json": metadata_json or "{}",
            "severity": severity,
            "scenario_type": scenario_type,
        },
    )
    return RedirectResponse(f"/datasets/{dataset_id}/cases/{case_id}", status_code=303)


@router.post("/{dataset_id}/cases/{case_id}/delete")
async def delete_case(dataset_id: int, case_id: int, session: SessionDep):
    case = svc.get_case(session, case_id)
    if not case or case.dataset_id != dataset_id:
        raise HTTPException(status_code=404, detail="Caso de teste não encontrado")
    svc.delete_case(session, case_id)
    return RedirectResponse(f"/datasets/{dataset_id}", status_code=303)


@router.post("/{dataset_id}/import")
async def import_file(
    request: Request,
    dataset_id: int,
    session: SessionDep,
    file: UploadFile,
):
    dataset = svc.get_dataset(session, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")

    content = (await file.read()).decode("utf-8", errors="ignore")
    filename = file.filename or ""

    if filename.endswith(".jsonl"):
        imported, errors = svc.import_jsonl(session, dataset_id, content)
    elif filename.endswith(".csv"):
        imported, errors = svc.import_csv(session, dataset_id, content)
    else:
        raise HTTPException(status_code=400, detail="Formato não suportado. Use .jsonl ou .csv")

    return render(
        request,
        "datasets/import_result.html",
        {
            "dataset": dataset,
            "imported": imported,
            "errors": errors,
        },
    )


@router.post("/{dataset_id}/delete")
async def delete_dataset(dataset_id: int, session: SessionDep):
    svc.delete_dataset(session, dataset_id)
    return RedirectResponse("/datasets/", status_code=303)
