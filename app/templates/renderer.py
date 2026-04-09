"""Configuração do Jinja2 e helper de render."""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).parent

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Filtros customizados
def format_float(value, decimals=4):
    if value is None:
        return "—"
    try:
        return f"{float(value):.{decimals}f}"
    except Exception:
        return str(value)

def format_ms(value):
    if value is None:
        return "—"
    return f"{float(value):.1f} ms"

def format_usd(value):
    if value is None:
        return "—"
    return f"${float(value):.6f}"

def metric_color(value, inverted=False):
    """Retorna classe CSS Tailwind baseada no valor 0-1."""
    if value is None:
        return "text-gray-400"
    v = float(value)
    if inverted:
        v = 1 - v
    if v >= 0.8:
        return "text-green-600 font-semibold"
    if v >= 0.5:
        return "text-yellow-600"
    return "text-red-600"

def judge_color(value):
    """Para notas 1-5."""
    if value is None:
        return "text-gray-400"
    v = float(value)
    if v >= 4:
        return "text-green-600 font-semibold"
    if v >= 3:
        return "text-yellow-600"
    return "text-red-600"

templates.env.filters["ff"] = format_float
templates.env.filters["ms"] = format_ms
templates.env.filters["usd"] = format_usd
templates.env.filters["metric_color"] = metric_color
templates.env.filters["judge_color"] = judge_color


def render(request: Request, template: str, context: dict):
    return templates.TemplateResponse(request, template, context)
