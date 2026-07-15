"""Rendu HTML -> PDF des CV via xhtml2pdf (fonctionne sous Windows)."""

from __future__ import annotations

import base64
import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import BASE_DIR, settings
from app.labels import labels_for
from app.schema import CV, Language, TemplateModel

TEMPLATES_DIR = BASE_DIR / "app" / "templates"
LOGOS_DIR = BASE_DIR / "app" / "static" / "logos"

# Configuration visuelle par modèle : template, logo et couleurs de marque.
MODEL_CONFIG = {
    TemplateModel.libens: {
        "template": "cv_libens.html",
        "logo": "libens.png",
        "orange": "#E8792B",
        "blue": "#2E75B6",
    },
    TemplateModel.compleo: {
        "template": "cv_compleo.html",
        "logo": "compleo.png",
        "orange": "#E8792B",
        "blue": "#1F6FC0",
    },
}

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _logo_data_uri(logo_name: str) -> str | None:
    p = LOGOS_DIR / logo_name
    if not p.exists():
        return None
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def apply_commercial_defaults(cv: CV, model: TemplateModel) -> CV:
    """Injecte le commercial Compleo par défaut quand les champs sont vides.

    Ne touche pas au modèle Libens (anonymisé, sans commercial). Toute valeur
    déjà présente (UI / requête) est conservée telle quelle.
    """
    if model != TemplateModel.compleo:
        return cv
    return cv.model_copy(
        update={
            "commercial_name": cv.commercial_name or settings.compleo_commercial_name or None,
            "commercial_email": cv.commercial_email or settings.compleo_commercial_email or None,
            "commercial_phone": cv.commercial_phone or settings.compleo_commercial_phone or None,
        }
    )


def render_html(cv: CV, model: TemplateModel, language: Language = Language.fr) -> str:
    cfg = MODEL_CONFIG[model]
    cv = apply_commercial_defaults(cv, model)
    tpl = _env.get_template(cfg["template"])
    return tpl.render(
        cv=cv,
        L=labels_for(language),
        logo_data_uri=_logo_data_uri(cfg["logo"]),
        orange=cfg["orange"],
        blue=cfg["blue"],
    )


def render_pdf(cv: CV, model: TemplateModel, language: Language = Language.fr) -> bytes:
    from xhtml2pdf import pisa

    html = render_html(cv, model, language)
    buf = io.BytesIO()
    status = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if status.err:
        raise RuntimeError(f"xhtml2pdf a renvoyé {status.err} erreurs")
    return buf.getvalue()
