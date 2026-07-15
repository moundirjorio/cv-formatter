"""Serveur MCP du CV Formatter.

Expose le service comme outils natifs pour un agent (Claude, Cursor…) :
- list_models()             -> modèles disponibles
- extract_cv(file_path)     -> CV structuré (JSON) depuis un fichier
- structure_cv_text(text)   -> CV structuré depuis du texte brut
- generate_cv(cv, model)    -> chemins des fichiers PDF + DOCX générés

Lancement : .venv\\Scripts\\python.exe mcp_server.py
"""

from __future__ import annotations

import uuid
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.extract import extract_text_from_file, structure_cv
from app.render_docx import render_docx
from app.render_pdf import MODEL_CONFIG, render_pdf
from app.schema import CV, Language, TemplateModel
from app.translate import translate_cv

mcp = FastMCP("cv-formatter")


@mcp.tool()
def list_models() -> list[dict]:
    """Liste les modèles de CV disponibles et leurs couleurs de marque."""
    return [
        {"id": m.value, "orange": c["orange"], "blue": c["blue"]}
        for m, c in MODEL_CONFIG.items()
    ]


@mcp.tool()
def extract_cv(file_path: str) -> dict:
    """Extrait et structure un CV depuis un fichier local (PDF, DOCX ou TXT).

    Retourne le CV structuré conforme au schéma (à vérifier/corriger avant génération).
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")
    text = extract_text_from_file(p.name, p.read_bytes())
    return structure_cv(text).model_dump()


@mcp.tool()
def structure_cv_text(text: str) -> dict:
    """Structure un CV fourni sous forme de texte brut. Retourne le CV structuré."""
    return structure_cv(text).model_dump()


@mcp.tool()
def translate_cv_content(cv: dict, target_language: str = "en") -> dict:
    """Traduit le contenu d'un CV entre 'fr' et 'en' (noms/dates/technos conservés)."""
    return translate_cv(CV.model_validate(cv), Language(target_language)).model_dump()


@mcp.tool()
def generate_cv(cv: dict, model: str = "libens", language: str = "fr") -> dict:
    """Génère le PDF et le DOCX d'un CV structuré selon le modèle choisi.

    cv       : objet CV (voir extract_cv / structure_cv_text)
    model    : 'libens' ou 'compleo'
    language : 'fr' ou 'en' — langue des libellés de sections
    Retourne les chemins absolus des fichiers générés.
    """
    tmpl = TemplateModel(model)
    lang = Language(language)
    cv_obj = CV.model_validate(cv)
    doc_id = uuid.uuid4().hex
    pdf_path = settings.outputs_dir / f"{doc_id}.pdf"
    docx_path = settings.outputs_dir / f"{doc_id}.docx"
    pdf_path.write_bytes(render_pdf(cv_obj, tmpl, lang))
    docx_path.write_bytes(render_docx(cv_obj, tmpl, lang))
    return {
        "id": doc_id,
        "model": tmpl.value,
        "language": lang.value,
        "pdf_path": str(pdf_path.resolve()),
        "docx_path": str(docx_path.resolve()),
    }


if __name__ == "__main__":
    mcp.run()
