"""Configuration du service (variables d'environnement)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    anthropic_api_key: str = ""
    cv_api_keys: str = "dev-key-changeme"
    claude_model: str = "claude-opus-4-8"
    app_env: str = "development"

    # Connexion à l'interface web (studio). Les appels /v1/* programmatiques
    # continuent d'utiliser X-API-Key ; la session navigateur, elle, ouvre
    # l'accès après login avec ces identifiants.
    login_user: str = "admin"
    login_password: str = "changeme"
    # Secret de signature du cookie de session (HMAC). À changer en production.
    session_secret: str = "dev-session-secret-change-me"
    # Durée de validité d'une session, en heures.
    session_hours: int = 12

    # Commercial Compleo par défaut : injecté sur tout CV Compleo dont le
    # champ commercial est vide (surchargeable dans l'UI / la requête).
    compleo_commercial_name: str = "Taha NORDINE"
    compleo_commercial_email: str = "t.nordine@compleotech.net"
    compleo_commercial_phone: str = "+33603437383"

    # Dossier de stockage persistant (comptes + CV générés). En production,
    # pointer DATA_DIR vers le disque persistant de l'hébergeur (ex: /var/data).
    # Vide = dossier ./storage local (développement).
    data_dir: str = ""

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.cv_api_keys.split(",") if k.strip()}

    @property
    def storage_dir(self) -> Path:
        return Path(self.data_dir) if self.data_dir else BASE_DIR / "storage"

    @property
    def outputs_dir(self) -> Path:
        return self.storage_dir / "outputs"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"


settings = Settings()
settings.outputs_dir.mkdir(parents=True, exist_ok=True)
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
