"""Rotas de datasets."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from app.db.engine import get_session
from app.models.entities import Dataset, ScenarioType, Severity, TestCase
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


@router.get("/{dataset_id}", response_class=HTMLResponse)
async def dataset_detail(request: Request, dataset_id: int, session: SessionDep):
    dataset = svc.get_dataset(session, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset não encontrado")
    cases = svc.list_cases(session, dataset_id)
    return render(request, "datasets/detail.html", {"dataset": dataset, "cases": cases})


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
        "severity": severity,
        "scenario_type": scenario_type,
    }
    svc.create_case(session, dataset_id, data)
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

    return render(request, "datasets/import_result.html", {
        "dataset": dataset,
        "imported": imported,
        "errors": errors,
    })


@router.post("/{dataset_id}/delete")
async def delete_dataset(dataset_id: int, session: SessionDep):
    svc.delete_dataset(session, dataset_id)
    return RedirectResponse("/datasets/", status_code=303)
