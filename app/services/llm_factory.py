import logging
from abc import ABC, abstractmethod
from typing import Dict, List
from app.core.config import settings

logger = logging.getLogger("uvicorn")

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass
    
    @property
    def name(self) -> str:
        return self.__class__.__name__

class GroqProvider(LLMProvider):
    def __init__(self):
        from groq import Groq
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.1-8b-instant"

    async def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
        )
        return response.choices[0].message.content
    
    @property
    def name(self) -> str:
        return "groq"

class OpenAIProvider(LLMProvider):
    def __init__(self):
        import openai
        openai.api_key = settings.OPENAI_API_KEY
        self.model = "gpt-3.5-turbo"

    async def generate(self, prompt: str) -> str:
        response = openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
        
    @property
    def name(self) -> str:
        return "openai"

class LLMOrchestrator:
    def __init__(self):
        self.providers = []
        # Ordre de priorité
        if settings.GROQ_API_KEY:
            self.providers.append(GroqProvider())
        if settings.OPENAI_API_KEY:
            self.providers.append(OpenAIProvider())

    async def generate_response(self, prompt: str) -> dict:
        errors = []
        for provider in self.providers:
            try:
                logger.info(f"Tentative de génération avec {provider.name}")
                response = await provider.generate(prompt)
                return {
                    "response": response,
                    "provider": provider.name,
                    "status": "success"
                }
            except Exception as e:
                logger.error(f"Echec {provider.name}: {str(e)}")
                errors.append(f"{provider.name}: {str(e)}")
                continue
        
        return {
            "response": "Désolé, nos services IA sont momentanément indisponibles.",
            "provider": "none",
            "status": "error",
            "debug_errors": errors
        }

    def get_status(self) -> Dict:
        """Retourne le statut des providers pour le frontend."""
        if not self.providers:
            return {"current": "none", "available": []}

        current_provider = self.providers[0].name
        available_providers = [p.name for p in self.providers]
        
        return {
            "current": current_provider,
            "available": available_providers
        }