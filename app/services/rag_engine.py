import logging
import re  
import numpy as np
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from sqlmodel import Session, select
from app.core.config import settings
from app.db.models import FAQItem

logger = logging.getLogger(__name__)

class RAGService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info(f"Chargement du modèle {settings.EMBEDDING_MODEL}...")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.faq_cache: List[Dict] = []
        self.question_embeddings = None
        self.answer_embeddings = None

    def reload_from_db(self, db: Session):
        """Recharge les embeddings depuis la base de données SQL."""
        logger.info("Mise à jour de l'index vectoriel depuis la DB...")
        faq_items = db.exec(select(FAQItem)).all()
        
        if not faq_items:
            logger.warning("Aucune FAQ trouvée en base.")
            return

        self.faq_cache = [{"id": item.id, "q": item.question, "a": item.answer} for item in faq_items]
        questions = [item["q"] for item in self.faq_cache]
        answers = [item["a"] for item in self.faq_cache]

        if questions:
            self.question_embeddings = self.model.encode(questions, convert_to_numpy=True)
            self.answer_embeddings = self.model.encode(answers, convert_to_numpy=True)
            logger.info(f"Index mis à jour : {len(self.faq_cache)} entrées.")
        else:
            logger.warning("FAQ vide, embeddings non générés.")

    @staticmethod
    def normalize_query(query: str) -> str:
        # Remplacement des caractères spéciaux par des espaces
        query = re.sub(r"[^\w\sàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ-]", " ", query)
        # Suppression des espaces multiples
        return re.sub(r"\s+", " ", query).strip()

    @staticmethod
    def is_too_short(text: str) -> bool:
        """Vérifie si le texte est trop court pour une recherche pertinente."""
        words = text.strip().split()
        return len(words) < 2 or len(text.strip()) < 5

    def search(self, query: str, threshold: float = 0.45) -> Dict:
        # Normalisation
        clean_query = self.normalize_query(query)
        q_lower = clean_query.lower().strip()

        # Gestion des réponses statiques (règles métier)
        greetings = {"bonjour", "hello", "salut", "hi", "bonsoir", "coucou"}
        short_acknowledgments = {"ok", "oui", "non", "merci", "merci beaucoup", "d'accord", "bien", "parfait", "super"}

        if q_lower in greetings:
            return {
                "answer": "Bonjour ! Comment puis-je vous aider ?",
                "confidence": 1.0,
                "matched_question": None,
                "provider": "static_rule"
            }
        
        if q_lower in short_acknowledgments:
            return {
                "answer": "Très bien ! Avez-vous d'autres questions ?",
                "confidence": 1.0,
                "matched_question": None,
                "provider": "static_rule"
            }
            
        if self.is_too_short(clean_query):
            return {
                "answer": "Pouvez-vous préciser votre question ?",
                "confidence": 0.0, 
                "matched_question": None,
                "provider": "static_rule"
            }

        # Recherche Vectorielle (si pas de réponse statique)
        if self.question_embeddings is None or len(self.faq_cache) == 0:
            return {"answer": None, "confidence": 0.0, "matched_question": None}

        query_vec = self.model.encode(clean_query, convert_to_numpy=True)

        q_norm = np.linalg.norm(self.question_embeddings, axis=1)
        a_norm = np.linalg.norm(self.answer_embeddings, axis=1)
        query_norm = np.linalg.norm(query_vec)
        
        q_sim = np.dot(self.question_embeddings, query_vec) / (q_norm * query_norm + 1e-9)
        a_sim = np.dot(self.answer_embeddings, query_vec) / (a_norm * query_norm + 1e-9)
        
        # Score hybride (70% question / 30% réponse)
        hybrid_scores = (0.7 * q_sim) + (0.3 * a_sim)
        best_idx = np.argmax(hybrid_scores)
        best_score = float(hybrid_scores[best_idx])

        if best_score >= threshold:
            match = self.faq_cache[best_idx]
            return {
                "answer": match["a"],
                "confidence": best_score,
                "matched_question": match["q"],
                "faq_id": match["id"]
            }
        
        return {"answer": None, "confidence": best_score, "matched_question": None}