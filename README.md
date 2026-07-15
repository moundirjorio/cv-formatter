# CV Formatter — SaaS

Reformate un CV candidat sur les **modèles de marque** (Libens Consulting, Compleo Technologies)
en **PDF** et **Word (.docx)**, avec les mêmes couleurs, logos et mise en page.

Conçu **API-first** : branchable dans n'importe quel agent via **API REST** ou **serveur MCP**.

## Fonctionnement

1. **Upload** d'un CV brut (PDF / DOCX / TXT) → l'**IA Claude** extrait et structure le contenu.
2. **Vérification / correction** guidée du contenu dans le studio.
3. **Choix** du modèle (Libens / Compleo) et traduction FR / EN.
4. **Prévisualisation automatique**, puis téléchargement PDF + DOCX.

L'interface est responsive, propose les thèmes clair et sombre et peut être
installée comme application web. Les pages authentifiées et les CV ne sont jamais
placés dans le cache hors ligne.

## Démarrer

```powershell
# 1. Configurer (copier .env.example -> .env et renseigner ANTHROPIC_API_KEY)
#    CV_API_KEYS = clés API acceptées (change-les !)

# 2. Lancer l'API + UI
.\run.ps1
```

- UI : http://127.0.0.1:8100 (connexion requise — voir ci-dessous)
- Doc API interactive : http://127.0.0.1:8100/docs

## Connexion (interface web)

L'interface `/` est protégée par une page de **connexion** (`/login`). Identifiants
par défaut (à changer dans `.env`) :

| Variable | Défaut | Rôle |
|---|---|---|
| `LOGIN_USER` | `admin` | Identifiant |
| `LOGIN_PASSWORD` | `changeme` | Mot de passe |
| `SESSION_SECRET` | *(dev)* | Secret HMAC de signature du cookie de session |
| `SESSION_HOURS` | `12` | Durée d'une session |

Après connexion, un cookie de session (`HttpOnly`, signé) autorise l'UI **et** les
appels `/v1/*` du navigateur — la clé API n'apparaît plus dans la page. Les appels
**programmatiques** (agents, MCP, cURL) continuent d'utiliser l'en-tête `X-API-Key`.
En production, mets `APP_ENV` ≠ `development` pour que le cookie passe en `Secure`.

### Création de compte

La page `/register` permet de créer un compte (identifiant + mot de passe). Les
comptes sont stockés dans `storage/users.json` avec **mots de passe hachés**
(PBKDF2-HMAC-SHA256, jamais en clair). L'inscription connecte automatiquement.

- Identifiant : 3–32 caractères (`A–Z a–z 0–9 . _ -`).
- Mot de passe : 8 caractères minimum.
- Le compte admin `.env` reste réservé et fonctionne indépendamment du fichier.

> `storage/users.json` est ignoré par git. L'inscription est **ouverte** : si le
> service est exposé publiquement, protège `/register` (VPN, reverse-proxy, ou
> désactivation) selon ton besoin.

## API REST

Les routes `/v1/*` acceptent soit la session web signée, soit l'en-tête
`X-API-Key` pour les appels programmatiques.

| Méthode | Route | Rôle |
|---|---|---|
| GET  | `/v1/models` | Liste les modèles + couleurs |
| POST | `/v1/cv/extract` | `multipart` fichier → CV structuré (JSON) |
| POST | `/v1/cv/translate` | `{cv, target_language}` → CV traduit |
| POST | `/v1/cv/generate` | `{cv, model}` → `{id, pdf_url, docx_url}` |
| GET  | `/v1/cv/{id}/download?fmt=pdf\|docx` | Télécharge le livrable |

### Exemple

```bash
# Extraire
curl -X POST http://127.0.0.1:8100/v1/cv/extract \
  -H "X-API-Key: dev-key-changeme" -F "file=@cv.pdf"

# Générer (JSON du CV dans body)
curl -X POST http://127.0.0.1:8100/v1/cv/generate \
  -H "X-API-Key: dev-key-changeme" -H "Content-Type: application/json" \
  -d '{"cv": { ... }, "model": "libens"}'
```

## Serveur MCP

Pour brancher le service comme outils natifs d'un agent :

```powershell
.\.venv\Scripts\python.exe mcp_server.py
```

Outils exposés : `list_models`, `extract_cv(file_path)`, `structure_cv_text(text)`,
`generate_cv(cv, model)`.

Config type (agent compatible MCP) :

```json
{
  "mcpServers": {
    "cv-formatter": {
      "command": "C:\\Users\\victus\\Desktop\\cv-formatter\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\victus\\Desktop\\cv-formatter\\mcp_server.py"]
    }
  }
}
```

## Modèles

| Modèle | Langue | Style |
|---|---|---|
| `libens` | FR / EN | Initiales, logo centré, titres orange majuscules, expériences en bleu |
| `compleo` | FR / EN | Nom complet, logo + contact en en-tête, titres orange soulignés, corps bleu |

Les logos sont dans `app/static/logos/` (`libens.png`, `compleo.png`).
> Le logo Compleo est un **placeholder** : remplace `app/static/logos/compleo.png` par le vrai fichier.
