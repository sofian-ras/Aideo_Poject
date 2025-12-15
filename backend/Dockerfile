# aideo/backend/Dockerfile

# Utilisation d'une image Python légère et rapide
FROM python:3.11-slim

# Définition du répertoire de travail à l'intérieur du conteneur
WORKDIR /app

# Copie et installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code de l'application
COPY app/ app/

# Le port que l'application FastAPI écoute
EXPOSE 8000

# La commande de démarrage est gérée par docker-compose (voir docker-compose.yml)
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]