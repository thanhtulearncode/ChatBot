# 🚀 Guide d'installation de Groq LLM

## Groq (API gratuite rapide)

**Avantages :** Très rapide, 30 req/min gratuit, aucune installation
**Inconvénient :** Nécessite connexion internet

### Installation :

```bash
# 1. Créer un compte gratuit
https://console.groq.com

# 2. Copier votre clé API depuis le dashboard

# 3. Ajouter dans .env
echo "GROQ_API_KEY=votre_clé_api_ici" >> .env

# 4. Installer le package
pip install groq
```

### Dans votre projet :

```python
llm_manager = LLMManager(preferred_provider="groq")
```

Le système utilise automatiquement Groq si la clé API est configurée.

---

## 🧪 Tester votre setup

```python
python -c "from llm_manager import LLMManager; m = LLMManager(); print(m.get_status())"
```

Devrait afficher les providers disponibles.
