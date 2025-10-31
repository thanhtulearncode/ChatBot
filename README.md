# 🤖 Chatbot RAG avec LLM

Un chatbot intelligent construit avec **FastAPI**, utilisant la technique **RAG (Retrieval-Augmented Generation)** combinant la recherche sémantique et la génération de texte par LLM (Large Language Model).

## ✨ Fonctionnalités

- 🔍 **Retrieval Engine** : Recherche sémantique dans la FAQ avec SentenceTransformers
- 🧠 **LLM Generation** : Génération de réponses naturelles avec Groq LLM (gratuit)
- 💾 **Memory Management** : Gestion de l'historique de conversation par utilisateur
- 🌐 **Interface Web** : Interface web moderne et conviviale
- 📊 **Hybrid Matching** : Combinaison de recherche dans les questions et réponses
- ⚡ **Caching** : Cache des embeddings pour optimiser les performances
- 🔄 **FAQ Dynamique** : Sauvegarde automatique des nouvelles questions et gestion
- 🎯 **Confidence Scoring** : Évaluation de la fiabilité des réponses

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │ (Interface Web)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastAPI    │ (main.py)
└──────┬──────┘
       │
       ├──► RetrievalEngine ──► SentenceTransformer ──► Base de données FAQ
       │
       ├──► MemoryManager ──► Historique de conversation
       │
       └──► LLMManager ──► API Groq
```

## 📋 Prérequis

- Python 3.8+
- pip
- Clé API depuis [Groq Console](https://console.groq.com) (gratuit)

## 🚀 Installation

### 1. Cloner le repository

```bash
git clone <repository-url>
cd ChatBot
```

### 2. Créer un environnement virtuel

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer la clé API

Créer un fichier `.env` à la racine :

```bash
# Copier depuis .env.example
cp .env.example .env
```

Ou créer manuellement et ajouter :

```env
GROQ_API_KEY=votre_clé_api_ici
```

**Obtenir une clé API :**
1. S'inscrire sur [Groq Console](https://console.groq.com)
2. Aller dans **API Keys** dans le tableau de bord
3. Copier la clé et la coller dans le fichier `.env`

### 5. Lancer l'application

```bash
python main.py
```

Ou utiliser uvicorn directement :

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Accéder à : http://127.0.0.1:8000

## 📁 Structure du projet

```
ChatBot/
├── main.py                 # Application FastAPI principale
├── llm_manager.py          # Gestion des providers LLM (Groq)
├── retrieval_engine.py     # Moteur de recherche sémantique
├── memory_manager.py       # Gestion de l'historique de conversation
├── requirements.txt        # Dépendances Python
├── .env.example           # Modèle pour les variables d'environnement
├── README.md              # Ce fichier
│
├── data/
│   ├── faq.json          # Base de données FAQ
│   └── new_questions.json # Questions nouvelles non encore ajoutées à la FAQ
│
├── templates/
│   └── index.html        # Interface web
│
├── static/
│   ├── css/
│   │   ├── chatbot.css   # Styles pour le chatbot
│   │   └── theme.css     # Thème général
│   └── js/
│       └── chatbot.js    # JavaScript pour le frontend
│
└── test/
    └── test_retrieval.py # Tests unitaires
```

## 🔧 Configuration

### Changer le modèle d'embedding

Dans `main.py`, vous pouvez changer le modèle SentenceTransformer :

```python
retriever = RetrievalEngine(
    faq_path="data/faq.json",
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

Modèles populaires :
- `paraphrase-multilingual-MiniLM-L12-v2` (multilingue, rapide)
- `all-MiniLM-L6-v2` (anglais, très rapide)
- `paraphrase-multilingual-mpnet-base-v2` (multilingue, plus précis mais plus lent)

### Changer le provider LLM

Par défaut utilise Groq. Pour changer dans `main.py` :

```python
llm_manager = LLMManager(preferred_provider="groq")
```

### Ajuster le seuil (Threshold)

Dans `retrieval_engine.py`, la fonction `get_best_match()` a un paramètre `threshold` (par défaut 0.45) :
- **Plus élevé** (0.6+) : Retourne uniquement les résultats très certains, plus de questions utiliseront le LLM
- **Plus bas** (0.3-) : Retourne plus de résultats, moins d'utilisation du LLM

## 📡 Points d'accès API

### Endpoints Chat

- `POST /chat` - Envoyer un message et recevoir une réponse
  ```json
  {
    "message": "Comment créer un compte ?",
    "user_id": "user123",
    "use_llm": true
  }
  ```

- `GET /` - Interface web

### Endpoints LLM

- `GET /llm/status` - Vérifier le statut des providers LLM
- `POST /llm/switch/{provider}` - Changer de provider LLM

### Endpoints Admin

- `GET /admin/new-questions` - Voir les nouvelles questions
- `POST /admin/add-to-faq/{question_index}` - Ajouter une question à la FAQ

### Endpoints Système

- `GET /health` - Vérification de santé
- `GET /metrics` - Statistiques du système

## 🧪 Tests

Lancer les tests :

```bash
pytest test/test_retrieval.py -v
```

## 🎯 Fonctionnement

1. **Phase Retrieval** : 
   - L'utilisateur envoie une question
   - Le système recherche dans la FAQ par similarité sémantique
   - Calcul du score de confiance

2. **Phase Generation** :
   - Si confidence < 0.45 : Utiliser le LLM pour répondre à une nouvelle question
   - Si confidence >= 0.45 : Utiliser le LLM pour améliorer la réponse de la FAQ (si activé)
   - Si pas de LLM : Retourner la réponse directement de la FAQ

3. **Mémoire** :
   - Sauvegarder l'historique de conversation par user_id
   - Conserver un maximum de 5 messages récents (configurable)

## 📊 Métriques et Monitoring

Accéder à `/metrics` pour voir :
- Nombre de requêtes traitées
- Distribution des scores de confiance
- Taux de réussite du cache
- Nombre d'utilisateurs actifs
- Statut des providers LLM

## 🔒 Sécurité

- ✅ Les clés API sont stockées dans `.env` (pas commitées dans git)
- ✅ CORS configuré (peut être restreint aux origines en production)
- ✅ Validation des entrées avec Pydantic
- ⚠️ **Production** : Devrait ajouter authentication/authorization

## 🚀 Déploiement

### Avec Docker (à venir)

```bash
docker build -t chatbot-rag .
docker run -p 8000:8000 --env-file .env chatbot-rag
```

### Avec Gunicorn

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Committer les changements (`git commit -m 'Add some AmazingFeature'`)
4. Pousser vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est publié sous licence MIT.

## 🙏 Remerciements

- [FastAPI](https://fastapi.tiangolo.com/)
- [SentenceTransformers](https://www.sbert.net/)
- [Groq](https://groq.com/) - API LLM gratuite
- [Uvicorn](https://www.uvicorn.org/)

## 📞 Support

Si vous rencontrez un problème :
1. Vérifier que le fichier `.env` contient `GROQ_API_KEY` correctement
2. Vérifier les logs dans la console
3. Lancer le health check : `GET /health`
4. Vérifier le statut LLM : `GET /llm/status`

## 🎓 Pour en savoir plus

- [Pattern RAG](https://www.promptingguide.ai/techniques/rag)
- [Sentence Transformers](https://www.sbert.net/docs/usage/semantic_textual_similarity.html)
- [Documentation FastAPI](https://fastapi.tiangolo.com/)

---

Fait avec ❤️ en utilisant Python & FastAPI
