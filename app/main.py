"""Service SaaS de formatage de CV — API REST (FastAPI) + UI web.

API-first : n'importe quel agent peut appeler /v1/cv/extract puis
/v1/cv/generate. Auth par clé API (header X-API-Key). Doc auto sur /docs.
"""

from __future__ import annotations

import uuid

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import users
from app.config import BASE_DIR, settings
from app.extract import extract_cv
from app.render_docx import render_docx
from app.render_pdf import MODEL_CONFIG, render_pdf
from app.schema import (
    CV,
    GenerateRequest,
    GenerateResponse,
    TemplateModel,
    TranslateRequest,
)
from app.security import (
    SESSION_COOKIE,
    check_credentials,
    current_user,
    make_session,
    require_api_key,
)
from app.translate import translate_cv

app = FastAPI(
    title="CV Formatter SaaS",
    version="1.0.0",
    description="Reformate un CV candidat sur les modèles de marque (Libens, Compleo). "
    "API-first, branchable dans n'importe quel agent.",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
_ui_env = Environment(
    loader=FileSystemLoader(BASE_DIR / "app" / "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


# ---------------------------------------------------------------- Auth (web)
def _set_session_cookie(resp: Response, username: str) -> None:
    resp.set_cookie(
        SESSION_COOKIE,
        make_session(username),
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.app_env != "development",
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return _ui_env.get_template("login.html").render(error=None, username="")


@app.post("/login", include_in_schema=False)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not check_credentials(username, password):
        html = _ui_env.get_template("login.html").render(
            error="Identifiant ou mot de passe incorrect.", username=username
        )
        return HTMLResponse(html, status_code=status.HTTP_401_UNAUTHORIZED)
    resp = RedirectResponse("/", status_code=303)
    _set_session_cookie(resp, username)
    return resp


@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    if current_user(request):
        return RedirectResponse("/", status_code=303)
    return _ui_env.get_template("register.html").render(error=None, username="")


@app.post("/register", include_in_schema=False)
async def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
):
    username = username.strip()
    error = (
        users.validate_new_username(username)
        or users.validate_password(password)
        or ("Les deux mots de passe ne correspondent pas." if password != password2 else None)
    )
    if error:
        html = _ui_env.get_template("register.html").render(
            error=error, username=username
        )
        return HTMLResponse(html, status_code=status.HTTP_400_BAD_REQUEST)
    users.add_user(username, password)
    # Connexion automatique après inscription.
    resp = RedirectResponse("/", status_code=303)
    _set_session_cookie(resp, username)
    return resp


@app.get("/logout", include_in_schema=False)
async def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


# ---------------------------------------------------------------- UI
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return _ui_env.get_template("ui.html").render(username=user)


# ---------------------------------------------------------------- API
@app.get("/v1/models")
async def list_models(_: str = Depends(require_api_key)):
    return {
        "models": [
            {"id": m.value, "colors": {"orange": c["orange"], "blue": c["blue"]}}
            for m, c in MODEL_CONFIG.items()
        ]
    }


@app.post("/v1/cv/extract", response_model=CV)
async def api_extract(
    file: UploadFile = File(...),
    _: str = Depends(require_api_key),
):
    """Extrait et structure un CV brut (PDF, DOCX ou TXT) via Claude."""
    data = await file.read()
    if not data:
        raise HTTPException(400, "Fichier vide.")
    try:
        return extract_cv(file.filename or "cv.txt", data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Échec de l'extraction : {exc}") from exc


@app.post("/v1/cv/translate", response_model=CV)
async def api_translate(
    req: TranslateRequest,
    _: str = Depends(require_api_key),
):
    """Traduit le contenu du CV vers la langue cible (fr/en) via Claude."""
    try:
        return translate_cv(req.cv, req.target_language)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Échec de la traduction : {exc}") from exc


@app.post("/v1/cv/generate", response_model=GenerateResponse)
async def api_generate(
    req: GenerateRequest,
    _: str = Depends(require_api_key),
):
    """Génère le PDF + DOCX pour le CV structuré et le modèle choisi."""
    doc_id = uuid.uuid4().hex
    pdf = render_pdf(req.cv, req.model, req.language)
    docx = render_docx(req.cv, req.model, req.language)
    (settings.outputs_dir / f"{doc_id}.pdf").write_bytes(pdf)
    (settings.outputs_dir / f"{doc_id}.docx").write_bytes(docx)
    return GenerateResponse(
        id=doc_id,
        model=req.model,
        pdf_url=f"/v1/cv/{doc_id}/download?fmt=pdf",
        docx_url=f"/v1/cv/{doc_id}/download?fmt=docx",
    )


@app.get("/v1/cv/{doc_id}/download", include_in_schema=True)
async def api_download(doc_id: str, fmt: str = "pdf", dl: int = 0):
    """Sert un livrable généré. L'identifiant (UUID) sert de jeton d'accès.

    Par défaut le fichier est servi en `inline` (permet l'aperçu PDF dans une
    iframe) ; passer `dl=1` force le téléchargement (Content-Disposition attachment).
    """
    if fmt not in ("pdf", "docx"):
        raise HTTPException(400, "fmt doit être 'pdf' ou 'docx'.")
    path = settings.outputs_dir / f"{doc_id}.{fmt}"
    if not path.exists():
        raise HTTPException(404, "Document introuvable.")
    media = "application/pdf" if fmt == "pdf" else (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path,
        media_type=media,
        filename=f"cv.{fmt}",
        content_disposition_type="attachment" if dl else "inline",
    )


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "models": [m.value for m in TemplateModel]}


# ---------------------------------------------------------------- PWA
_MANIFEST = {
    "name": "CV Formatter — Studio",
    "short_name": "CV Formatter",
    "description": "Reformate un CV sur les modèles de marque (Libens, Compleo).",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f5f6f8",
    "theme_color": "#5b5cf0",
    "icons": [
        {"src": "/static/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
    ],
}

# Service worker : seules les ressources publiques sont mises en cache. Les pages
# authentifiées, CV et exports restent toujours hors cache pour protéger les données.
_SW_JS = """
const C='cvf-v2';
const PUBLIC=['/static/icon.svg','/manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(PUBLIC)).then(()=>self.skipWaiting()));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin!==location.origin||(!url.pathname.startsWith('/static/')&&url.pathname!=='/manifest.webmanifest'))return;
  e.respondWith(fetch(req).then(res=>{if(res.ok){const cp=res.clone();caches.open(C).then(c=>c.put(req,cp));}return res;}).catch(()=>caches.match(req)));
});
"""


@app.get("/manifest.webmanifest", include_in_schema=False)
async def manifest():
    return JSONResponse(_MANIFEST, media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    return Response(
        _SW_JS,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )
