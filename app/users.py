"""Magasin d'utilisateurs pour la connexion au studio.

Stockage volontairement simple : un fichier JSON ``storage/users.json`` avec
mots de passe hachés en **PBKDF2-HMAC-SHA256** (stdlib, aucune dépendance).
Suffisant pour un service mono-instance ; pour du multi-instance/haute charge,
remplacer par une vraie base.

Le compte admin défini dans ``.env`` (``LOGIN_USER`` / ``LOGIN_PASSWORD``) reste
géré à part dans ``security.py`` : il fonctionne même si ce fichier est vide.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timezone

from app.config import settings

_PBKDF2_ROUNDS = 200_000
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD_LEN = 8


def _store_path():
    return settings.storage_dir / "users.json"


def _load() -> dict:
    path = _store_path()
    if not path.exists():
        return {"users": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"users": {}}
    data.setdefault("users", {})
    return data


def _save(data: dict) -> None:
    _store_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ------------------------------------------------------------------ hachage
def _hash(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS
    )
    return dk.hex()


# ------------------------------------------------------------------ API
def user_exists(username: str) -> bool:
    return username in _load()["users"]


def validate_new_username(username: str) -> str | None:
    """Retourne un message d'erreur si l'identifiant est invalide, sinon ``None``."""
    if not _USERNAME_RE.match(username or ""):
        return (
            "L'identifiant doit faire 3 à 32 caractères "
            "(lettres, chiffres, . _ - uniquement)."
        )
    # Réservé au compte admin intégré (.env).
    if username == settings.login_user:
        return "Cet identifiant est réservé."
    if user_exists(username):
        return "Cet identifiant est déjà utilisé."
    return None


def validate_password(password: str) -> str | None:
    if len(password or "") < MIN_PASSWORD_LEN:
        return f"Le mot de passe doit faire au moins {MIN_PASSWORD_LEN} caractères."
    return None


def add_user(username: str, password: str) -> None:
    """Crée un utilisateur. L'appelant doit avoir validé au préalable."""
    data = _load()
    salt = secrets.token_hex(16)
    data["users"][username] = {
        "salt": salt,
        "hash": _hash(password, salt),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _save(data)


def verify_user(username: str, password: str) -> bool:
    """Vérifie les identifiants d'un utilisateur du magasin (temps ~constant)."""
    rec = _load()["users"].get(username)
    if not rec:
        # Calcul factice pour limiter la fuite temporelle sur l'existence du compte.
        _hash(password, secrets.token_hex(16))
        return False
    return hmac.compare_digest(_hash(password, rec["salt"]), rec.get("hash", ""))
