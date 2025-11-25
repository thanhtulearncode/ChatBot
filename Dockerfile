# Utiliser une image Python officielle légère
FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Variables d'environnement pour Python
# PYTHONDONTWRITEBYTECODE: Évite les fichiers .pyc inutiles
# PYTHONUNBUFFERED: Les logs s'affichent directement dans la console
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installation des dépendances système (nécessaire pour certaines libs python)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copier tout le code du projet dans le conteneur
COPY . .

# Exposer le port 8000
EXPOSE 8000

# Commande de lancement
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]