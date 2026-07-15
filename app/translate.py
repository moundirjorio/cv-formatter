"""Traduction du contenu d'un CV entre français et anglais via Claude.

Traduit les champs rédactionnels (titre, synthèse, expériences, compétences…)
en conservant les noms propres, emails, dates, technologies et le contact
commercial. Réutilise l'outil `emit_cv` pour une sortie structurée conforme.
"""

from __future__ import annotations

from app.config import settings
from app.extract import _anthropic, _cv_tool
from app.schema import CV, Language

_LANG_NAME = {Language.fr: "français", Language.en: "anglais"}


def translate_cv(cv: CV, target: Language) -> CV:
    lang = _LANG_NAME[target]
    system = (
        f"Tu traduis un CV en {lang}. Renvoie le CV structuré via l'outil.\n"
        "Règles :\n"
        f"- Traduis en {lang} tous les textes rédactionnels : title, summary, "
        "experience_highlights, catégories et items de compétences, role, context, "
        "responsibilities, tech_environment, degree, school, certifications, languages.\n"
        "- NE traduis PAS : les noms propres (entreprises, écoles, personnes), "
        "initials, full_name, email, phone, commercial_name, commercial_email, "
        "commercial_phone, les dates/périodes, les noms de technologies et de produits "
        "(Salesforce, Intune, Microsoft 365, LWC, Apex…).\n"
        "- Adapte les intitulés de langues au format cible "
        "(ex: 'Français – Natif' <-> 'French – Native').\n"
        "- Conserve strictement la même structure et le même ordre."
    )
    tool = _cv_tool()
    msg = _anthropic().messages.create(
        model=settings.claude_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system,
        tools=[tool],
        tool_choice={"type": "auto"},
        messages=[
            {
                "role": "user",
                "content": "CV à traduire (JSON) :\n" + cv.model_dump_json(exclude_none=False),
            }
        ],
    )
    for block in msg.content:
        if block.type == "tool_use" and block.name == "emit_cv":
            out = CV.model_validate(block.input)
            # Sécurité : on ne laisse pas l'IA altérer le contact commercial.
            out.commercial_name = cv.commercial_name
            out.commercial_email = cv.commercial_email
            out.commercial_phone = cv.commercial_phone
            return out
    raise RuntimeError("Traduction : Claude n'a pas renvoyé de CV structuré.")
