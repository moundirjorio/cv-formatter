"""Schéma structuré d'un CV, commun aux deux modèles (Libens, Compleo).

Ce schéma est le contrat pivot : l'extraction IA le remplit, les
générateurs PDF/DOCX le consomment. Tout est optionnel sauf le titre,
pour tolérer des CV incomplets.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TemplateModel(str, Enum):
    libens = "libens"
    compleo = "compleo"


class Language(str, Enum):
    fr = "fr"
    en = "en"


class SkillGroup(BaseModel):
    category: str = Field(..., description="Catégorie de compétences, ex: 'Microsoft 365 Services'")
    items: list[str] = Field(default_factory=list, description="Liste des compétences")


class Experience(BaseModel):
    company: str = ""
    role: str = ""
    location: str | None = None
    period: str | None = Field(None, description="Ex: 'December 2024 – Present'")
    context: str | None = Field(None, description="Paragraphe de contexte de la mission")
    responsibilities: list[str] = Field(default_factory=list)
    tech_environment: str | None = Field(None, description="Environnement technique, texte libre")


class Education(BaseModel):
    degree: str = ""
    school: str | None = None
    period: str | None = None


class CV(BaseModel):
    # Identité
    full_name: str | None = Field(None, description="Nom réel (affiché sur Compleo, masqué sur Libens)")
    initials: str = Field("", description="Code anonymisé affiché comme titre, ex: 'RBJ', 'P.B.Y'")
    title: str = Field(..., description="Intitulé du poste, ex: 'Consultant Salesforce Senior'")
    email: str | None = None
    phone: str | None = None

    # Commercial / contact Compleo (affiché en haut à droite du modèle Compleo).
    # Ce n'est PAS le candidat mais le consultant/commercial qui présente le profil.
    commercial_name: str | None = None
    commercial_email: str | None = None
    commercial_phone: str | None = None

    # Contenu
    summary: str = Field("", description="Résumé / synthèse professionnelle (multi-paragraphes ok)")
    experience_highlights: list[str] = Field(
        default_factory=list, description="Résumé des expériences en une ligne chacune"
    )
    skill_groups: list[SkillGroup] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    cv: CV
    model: TemplateModel = TemplateModel.libens
    language: Language = Field(
        Language.fr, description="Langue des libellés de sections (fr/en)"
    )


class GenerateResponse(BaseModel):
    id: str
    model: TemplateModel
    pdf_url: str
    docx_url: str


class TranslateRequest(BaseModel):
    cv: CV
    target_language: Language
