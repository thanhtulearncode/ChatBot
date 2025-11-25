# Chatbot RAG : Production Ready

Un assistant intelligent, robuste et modulaire construit avec **FastAPI**. Il combine la recherche sémantique (**RAG**) et la génération par IA (**LLM**) pour fournir des réponses précises et contextuelles.

## Fonctionnalités Clés

- **Intelligence Hybride** : Moteur RAG (SentenceTransformers) + LLM (Groq) avec bascule automatique.
- **Sécurité & Auth** : Interface administrateur protégée par JWT (Access Tokens & Cookies).
- **Dashboard Admin** : Statistiques en temps réel et gestion (CRUD) de la FAQ sans redémarrage.
- **Interface Moderne** : UI "Glassmorphism", support Markdown et feedback utilisateur.
- **Dockerisé** : Déploiement facile avec Docker Compose.
- **Persistance** : Base de données SQLite/SQLModel pour l'historique et la FAQ.

## Configuration du LLM

Ce projet utilise **Groq** par défaut pour sa rapidité et sa gratuité, avec un fallback possible sur **OpenAI**.

### Option 1 : Groq (Recommandé)

L'API est très rapide et offre un quota gratuit généreux.

1.  Créez un compte sur [Groq Console](https://console.groq.com).
2.  Allez dans la section **API Keys** et cliquez sur **Create API Key**.
3.  Copiez votre clé (commençant par `gsk_`).
4.  Collez-la dans votre fichier `.env` :
    ```ini
    GROQ_API_KEY="gsk_votre_cle_ici..."
    ```

### Option 2 : OpenAI (Backup)

Si vous préférez GPT-3.5/4 ou souhaitez un backup de sécurité.

1.  Ajoutez votre clé OpenAI dans le fichier `.env` :
    ```ini
    OPENAI_API_KEY="sk-..."
    ```
2.  Le système utilisera automatiquement OpenAI si Groq est indisponible ou non configuré.

---

## Installation Rapide (Docker)

C'est la méthode recommandée pour tester et déployer.

**1. Cloner le projet**

```bash
git clone https://github.com/thanhtulearncode/ChatBot.git
cd ChatBot
```

**2. Configurer l'environnement**
Créez votre fichier `.env` à partir de l'exemple :

```bash
cp .env.example .env
# Éditez le fichier .env pour y ajouter votre GROQ_API_KEY
```

**3. Lancer l'application**

```bash
docker-compose up --build
```

**4. Initialiser la base de données (Premier lancement uniquement)**
Ouvrez un nouveau terminal et exécutez :

```bash
# Import de la FAQ initiale
docker-compose exec chatbot python scripts/init_db.py

# Création de l'admin
docker-compose exec chatbot python scripts/create_admin.py
```

## Accès

- **Chatbot (Utilisateur)** : [http://localhost:8000](https://www.google.com/search?q=http://localhost:8000)
- **Dashboard (Admin)** : [http://localhost:8000/api/auth/login](https://www.google.com/search?q=http://localhost:8000/api/auth/login)
  - _Compte par défaut_ : `admin@chatbot.com` / `admin123`
- **Documentation API** : [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)

## Installation Locale (Développement)

Si vous préférez coder sans Docker :

```bash
# 1. Créer l'environnement virtuel
python -m venv venv
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Initialiser la DB
python scripts/init_db.py
python scripts/create_admin.py

# 4. Lancer le serveur
uvicorn app.main:app --reload
```

## Structure du Projet

```text
/ChatBot
├── app/                    # Cœur de l'application
│   ├── core/               # Config & Sécurité
│   ├── db/                 # Modèles & Session SQL
│   ├── routers/            # Endpoints (Chat, Admin, Auth)
│   ├── services/           # Logique RAG & LLM
│   └── main.py             # Point d'entrée
├── data/                   # Données (DB & JSON source)
├── scripts/                # Scripts d'initialisation
├── static/                 # Assets Frontend (CSS/JS)
├── templates/              # Pages HTML (Jinja2)
├── tests/                  # Tests unitaires (Pytest)
├── docker-compose.yml      # Orchestration Docker
└── Dockerfile              # Image Python
```

## Tests

Pour vérifier que tout fonctionne correctement (nécessite l'installation locale) :

```bash
pytest
```

## Contribution

Les contributions sont les bienvenues \! N'hésitez pas à ouvrir une **Issue** ou une **Pull Request**.

---

_Propulsé par FastAPI, SentenceTransformers & Groq._
