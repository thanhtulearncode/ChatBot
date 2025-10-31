"""
Gestionnaire de LLM Groq
"""
import os
from pathlib import Path
from typing import Dict, List
from abc import ABC, abstractmethod
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_env_force():
    """Charge le fichier .env"""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            env_path = Path.cwd() / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            logger.info(f"✅ Fichier .env chargé depuis: {env_path}")
        else:
            logger.warning("⚠️ Fichier .env non trouvé.")
    except ImportError:
        env_path = Path(__file__).parent / ".env"
        if not env_path.exists():
            env_path = Path.cwd() / ".env"

        if env_path.exists():
            logger.info(f"🔍 Lecture manuelle du fichier .env depuis: {env_path}")
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            os.environ[key] = value
                logger.info("✅ Fichier .env chargé avec succès (mode manuel)")
            except Exception as e:
                logger.error(f"❌ Erreur lecture .env: {e}")
        else:
            logger.warning("⚠️ Fichier .env non trouvé.")


load_env_force()


class BaseLLM(ABC):
    """Classe de base pour tous les LLMs"""
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Génère une réponse"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le LLM est disponible"""
        pass


class GroqLLM(BaseLLM):
    """Groq Cloud - API gratuite avec limites généreuses"""
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        self.model_name = model_name
        self.api_key = os.getenv("GROQ_API_KEY")

        logger.info(f"🔑 GROQ_API_KEY présente: {'OUI' if self.api_key else 'NON'}")

        if not self.api_key:
            logger.warning("GROQ_API_KEY non définie")
            self.available = False
        else:
            try:
                from groq import Groq
                logger.info("✅ Module groq importé avec succès")

                self.client = Groq(api_key=self.api_key)
                logger.info("✅ Client Groq créé")

                logger.info("🧪 Test de connexion Groq...")
                test_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "Réponds juste 'OK'"}],
                    max_tokens=5
                )
                logger.info("✅ Test de connexion Groq réussi")
                self.available = True

            except ImportError as e:
                logger.error(f"❌ Erreur import groq: {e}")
                self.available = False
            except Exception as e:
                logger.error(f"❌ Erreur initialisation Groq: {e}")
                self.available = False

    def is_available(self) -> bool:
        return self.available

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Génère avec Groq"""
        if not self.is_available():
            return "Erreur : Groq non configuré"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Erreur Groq: {e}")
            return f"Erreur de génération : {str(e)}"


class LLMManager:
    """Gestionnaire pour le LLM Groq avec RAG"""
    def __init__(self, preferred_provider: str = "auto"):
        self.providers = {}
        self.preferred = preferred_provider
        self.current_provider = None

        self._init_providers()
        self._select_best_provider()
        self._log_final_status()

    def _init_providers(self):
        """Initialise le provider Groq"""
        logger.info("🔍 Initialisation du LLM Groq...")

        groq = GroqLLM()
        if groq.is_available():
            self.providers["groq"] = groq
            logger.info("  ✅ Groq configuré")
        else:
            logger.warning("  ❌ Groq non disponible")

    def _select_best_provider(self):
        """Sélectionne le provider"""
        if self.preferred != "auto" and self.preferred in self.providers:
            self.current_provider = self.preferred
            return

        if "groq" in self.providers:
            self.current_provider = "groq"
            return

        self.current_provider = None

    def _log_final_status(self):
        """Log le statut final"""
        if self.current_provider == "groq":
            logger.info("🎯 Provider sélectionné : Groq")
        else:
            logger.error("❌ Groq non disponible - Mode RAG désactivé")

    def generate_response(
        self,
        question: str,
        context: str,
        max_tokens: int = 500
    ) -> Dict:
        """Génère une réponse en utilisant le RAG pattern"""
        if not self.current_provider:
            return {
                "response": "Désolé, Groq n'est pas actuellement disponible. Veuillez vérifier la configuration de la clé API GROQ_API_KEY.",
                "provider": "none",
                "confidence": 0.0
            }

        prompt = self._build_rag_prompt(question, context)
        provider = self.providers[self.current_provider]
        response = provider.generate(prompt, max_tokens)

        return {
            "response": response,
            "provider": self.current_provider,
            "confidence": 0.9
        }

    def _build_rag_prompt(self, question: str, context: str) -> str:
        """Construit un prompt optimisé pour RAG"""
        if context:
            prompt = f"""Tu es un assistant virtuel serviable et professionnel.

Contexte :
{context}

Question de l'utilisateur :
{question}

Instructions :
- Utilise UNIQUEMENT les informations du contexte pour répondre
- Sois concis mais complet (2-3 phrases)
- Si le contexte ne contient pas l'information, dis-le clairement
- Reste poli et professionnel
- Réponds en français

Réponse :"""
        else:
            prompt = f"""Tu es un assistant virtuel serviable et professionnel.

Question de l'utilisateur :
{question}

Instructions :
- Réponds de manière utile et précise à la question
- Sois concis mais complet (2-3 phrases)
- Si tu ne connais pas la réponse, propose de contacter le support
- Reste poli et professionnel
- Réponds en français

Réponse :"""

        return prompt

    def get_available_providers(self) -> List[str]:
        """Retourne la liste des providers disponibles"""
        return list(self.providers.keys())

    def switch_provider(self, provider_name: str) -> bool:
        """Change de provider"""
        if provider_name in self.providers:
            self.current_provider = provider_name
            logger.info(f"🔄 Provider changé vers : {provider_name}")
            return True
        return False

    def get_status(self) -> Dict:
        """Retourne le statut de tous les providers"""
        return {
            "current": self.current_provider,
            "available": self.get_available_providers(),
            "details": {
                name: {
                    "available": provider.is_available(),
                    "model": getattr(provider, 'model_name', 'N/A')
                }
                for name, provider in self.providers.items()
            }
        }
