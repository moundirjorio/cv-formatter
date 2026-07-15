"""Authentification du service.

Deux voies coexistent :

* **X-API-Key** — pour les appels programmatiques (agents, MCP, cURL).
* **Session par cookie signé** — pour l'interface web (studio), ouverte après
  connexion via ``/login``. Le cookie est signé en HMAC-SHA256 avec
  ``settings.session_secret`` (aucune dépendance externe).

Les routes ``/v1/*`` acceptent l'une **ou** l'autre : un navigateur connecté
n'a donc pas besoin de manipuler la clé API.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException, Request, status

from app import users
from app.config import settings

SESSION_COOKIE = "cvf_session"


# ------------------------------------------------------------------ session
def _sign(payload: str) -> str:
    return hmac.new(
        settings.session_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


def make_session(username: str) -> str:
    """Fabrique un jeton de session signé pour ``username``."""
    data = {"u": username, "exp": int(time.time()) + settings.session_hours * 3600}
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    return f"{payload}.{_sign(payload)}"


def read_session(token: str | None) -> str | None:
    """Retourne le nom d'utilisateur si le jeton est valide et non expiré."""
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(payload)):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(data.get("exp", 0)) < time.time():
        return None
    return data.get("u")


def current_user(request: Request) -> str | None:
    """Utilisateur connecté d'après le cookie de session, ou ``None``."""
    return read_session(request.cookies.get(SESSION_COOKIE))


def check_credentials(username: str, password: str) -> bool:
    """Vérifie les identifiants de connexion.

    Deux sources : le compte admin intégré (``.env``) et les comptes créés via
    ``/register`` (magasin ``users.json``).
    """
    if hmac.compare_digest(username, settings.login_user):
        return hmac.compare_digest(password, settings.login_password)
    return users.verify_user(username, password)


# ------------------------------------------------------------------ dépendance API
async def require_api_key(
    request: Request, x_api_key: str | None = Header(None)
) -> str:
    """Autorise la requête via clé API **ou** session navigateur valide."""
    if x_api_key and x_api_key in settings.api_keys:
        return x_api_key
    user = current_user(request)
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise (clé API X-API-Key ou session).",
    )
