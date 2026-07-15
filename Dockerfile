# Image de déploiement — Hugging Face Spaces (SDK Docker).
# HF sert l'app sur le port 7860 en HTTPS.
FROM python:3.12-slim

# HF Spaces exécute le conteneur avec l'utilisateur 1000 : on le crée et on
# travaille dans son dossier, sinon l'écriture (comptes, CV générés) échoue.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DATA_DIR=/home/user/app/storage

WORKDIR /home/user/app

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user:user . .

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
