"""Rota de configurações."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.db.engine import get_session
from app.models.entities import AppSetting
from app.services.llm.registry import AVAILABLE_PROVIDERS
from app.templates.renderer import render

router = APIRouter(prefix="/settings", tags=["settings"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request, session: SessionDep):
    db_settings = session.exec(select(AppSetting)).all()
    return render(request, "settings.html", {
        "config": settings,
        "db_settings": db_settings,
        "providers": AVAILABLE_PROVIDERS,
    })


@router.post("/")
async def update_setting(
    session: SessionDep,
    key: str = Form(...),
    value: str = Form(...),
):
    from datetime import datetime, timezone
    existing = session.get(AppSetting, key)
    if existing:
        existing.value = value
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
    else:
        session.add(AppSetting(key=key, value=value))
    session.commit()
    return RedirectResponse("/settings/", status_code=303)
