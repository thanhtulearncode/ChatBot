"""
Retrieval Engine
Utilise SentenceTransformer pour faire correspondre les requêtes aux FAQ.
"""
import json
import pickle
import hashlib
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RECOMMENDED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

class RetrievalEngine:
    """Retrieval basé sur embeddings avec cache et hybrid matching (questions + réponses)."""

    def __init__(self, faq_path: str, model_name: str = RECOMMENDED_MODEL):
        self.faq_path = faq_path
        self.model = SentenceTransformer(model_name)

        self.faq_data: List[Dict] = []
        self.question_embeddings: Optional[np.ndarray] = None
        self.answer_embeddings: Optional[np.ndarray] = None

        self.stats = {
            "total_queries": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0
        }

        self.query_cache: Dict[str, np.ndarray] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_path = Path("cache/embeddings_cache.pkl")

        self.load_and_index()
        self.load_cache()

    def load_and_index(self):
        """Charge la FAQ et crée les embeddings des questions et réponses."""
        logger.info(f"Chargement de la FAQ depuis {self.faq_path}")
        try:
            with open(self.faq_path, "r", encoding="utf-8") as f:
                self.faq_data = json.load(f)

            questions = [item["question"] for item in self.faq_data]
            answers = [item["answer"] for item in self.faq_data]

            logger.info(f"Encodage de {len(questions)} questions et réponses...")
            self.question_embeddings = self.model.encode(
                questions, convert_to_numpy=True, show_progress_bar=True, batch_size=32
            )
            self.answer_embeddings = self.model.encode(
                answers, convert_to_numpy=True, show_progress_bar=True, batch_size=32
            )

            logger.info(f"Index créé avec {len(self.faq_data)} entrées.")

        except Exception as e:
            logger.error(f"Erreur lors du chargement de la FAQ : {e}")
            self.faq_data = []
            self.question_embeddings = None
            self.answer_embeddings = None

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcule la similarité cosinus entre deux vecteurs."""
        dot = np.dot(vec1, vec2)
        norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return float(dot / norm) if norm else 0.0

    @staticmethod
    def normalize_query(query: str) -> str:
        """Nettoie la requête utilisateur."""
        query = re.sub(r"[^\w\sàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ-]", " ", query)
        return re.sub(r"\s+", " ", query).strip()

    @staticmethod
    def is_too_short(text: str) -> bool:
        """Vérifie si le texte est trop court pour être significatif."""
        words = text.strip().split()
        return len(words) < 2 or len(text.strip()) < 5

    def _hash_text(self, text: str) -> str:
        """Crée un hash pour le cache."""
        return hashlib.md5(text.encode()).hexdigest()

    def encode_with_cache(self, text: str) -> np.ndarray:
        """Encode un texte avec cache local."""
        text_hash = self._hash_text(text)
        if text_hash in self.query_cache:
            self.cache_hits += 1
            return self.query_cache[text_hash]

        self.cache_misses += 1
        embedding = self.model.encode(text, convert_to_numpy=True)

        if len(self.query_cache) > 1000:
            self.query_cache.pop(next(iter(self.query_cache)))  # FIFO

        self.query_cache[text_hash] = embedding
        return embedding

    def get_best_match(
        self, query: str, context_history: Optional[List[Dict]] = None, threshold: float = 0.45
    ) -> Dict:
        """Trouve la meilleure correspondance dans la FAQ."""
        self.stats["total_queries"] += 1
        query = self.normalize_query(query)

        if not self.faq_data or self.question_embeddings is None:
            return {"answer": "Base de connaissances indisponible.", "confidence": 0.0, "matched_question": None}

        q_lower = query.lower()
        if q_lower in {"bonjour", "hello", "salut", "hi", "bonsoir"}:
            return {"answer": "Bonjour ! Comment puis-je vous aider ?", "confidence": 1.0, "matched_question": None}
        if q_lower in {"ok", "oui", "non", "merci", "d’accord", "bien"}:
            return {"answer": "Souhaitez-vous plus de précisions ?", "confidence": 1.0, "matched_question": None}
        if self.is_too_short(query):
            return {"answer": "Pouvez-vous préciser votre question ?", "confidence": 0.0, "matched_question": None}

        query_embedding = self.encode_with_cache(query)

        scores = []
        for i in range(len(self.question_embeddings)):
            q_sim = self.cosine_similarity(query_embedding, self.question_embeddings[i])
            a_sim = self.cosine_similarity(query_embedding, self.answer_embeddings[i])
            hybrid = 0.7 * q_sim + 0.3 * a_sim
            scores.append((i, hybrid))

        scores.sort(key=lambda x: x[1], reverse=True)
        best_idx, best_score = scores[0]

        # Statistiques de confiance
        if best_score > 0.7:
            self.stats["high_confidence"] += 1
        elif best_score > 0.45:
            self.stats["medium_confidence"] += 1
        else:
            self.stats["low_confidence"] += 1

        if best_score >= threshold:
            return {
                "answer": self.faq_data[best_idx]["answer"],
                "confidence": float(best_score),
                "matched_question": self.faq_data[best_idx]["question"],
            }

        top_suggestions = [self.faq_data[idx]["question"] for idx, _ in scores[:2]]
        suggestion_text = "\n".join(f"• {q}" for q in top_suggestions)
        return {
            "answer": (
                "Je n’ai pas trouvé de réponse précise à votre question.\n"
                f"Voici quelques suggestions :\n{suggestion_text}"
            ),
            "confidence": float(best_score),
            "matched_question": None,
        }

    def get_top_k_matches(self, query: str, k: int = 3) -> List[Dict]:
        """Retourne les k meilleures correspondances."""
        if not self.faq_data or self.question_embeddings is None:
            return []

        query = self.normalize_query(query)
        query_embedding = self.encode_with_cache(query)

        hybrid_scores = []
        for i in range(len(self.question_embeddings)):
            q_sim = self.cosine_similarity(query_embedding, self.question_embeddings[i])
            a_sim = self.cosine_similarity(query_embedding, self.answer_embeddings[i])
            hybrid = 0.7 * q_sim + 0.3 * a_sim
            hybrid_scores.append({
                "question": self.faq_data[i]["question"],
                "answer": self.faq_data[i]["answer"],
                "confidence": float(hybrid),
            })

        hybrid_scores.sort(key=lambda x: x["confidence"], reverse=True)
        return hybrid_scores[:k]

    def get_stats(self) -> Dict:
        """Retourne les statistiques d’utilisation."""
        return self.stats

    def get_cache_stats(self) -> Dict:
        """Retourne les statistiques du cache."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total else 0
        return {
            "cache_size": len(self.query_cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }

    def save_cache(self):
        """Sauvegarde le cache sur disque."""
        self.cache_path.parent.mkdir(exist_ok=True)
        with open(self.cache_path, "wb") as f:
            pickle.dump(self.query_cache, f)
        logger.info(f"Cache sauvegardé ({len(self.query_cache)} entrées).")

    def load_cache(self):
        """Charge le cache depuis le disque."""
        if not self.cache_path.exists():
            self.query_cache = {}
            return
        try:
            with open(self.cache_path, "rb") as f:
                self.query_cache = pickle.load(f)
            logger.info(f"Cache chargé ({len(self.query_cache)} entrées).")
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du cache : {e}")
            self.query_cache = {}
