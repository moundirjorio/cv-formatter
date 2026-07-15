"""Libellés de sections traduits (FR / EN), partagés PDF + DOCX.

La langue pilote les intitulés de sections ET les sous-libellés d'expérience.
Le style (majuscules Libens, souligné Compleo) reste géré côté modèle.
"""

from __future__ import annotations

from app.schema import Language

LABELS = {
    Language.fr: {
        "summary": "Synthèse",
        "highlights": "Résumé des expériences",
        "skills": "Compétences techniques",
        "education": "Formation",
        "certs": "Certifications",
        "langs": "Langues",
        "experience": "Expérience professionnelle",
        "context": "Contexte",
        "responsibilities": "Responsabilités",
        "tech": "Environnement technique",
    },
    Language.en: {
        "summary": "Professional Summary",
        "highlights": "Experience Summary",
        "skills": "Technical Skills",
        "education": "Education",
        "certs": "Certifications",
        "langs": "Languages",
        "experience": "Professional Experience",
        "context": "Context",
        "responsibilities": "Key Responsibilities",
        "tech": "Technical Environment",
    },
}


def labels_for(language: Language | str) -> dict:
    if isinstance(language, str):
        language = Language(language)
    return LABELS[language]
