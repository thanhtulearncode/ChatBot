import logging
import re
import chromadb
from typing import Dict
from sentence_transformers import SentenceTransformer
from sqlmodel import Session, select
from app.core.config import settings
from app.db.models import FAQItem

logger = logging.getLogger(__name__)


class RAGService:
    """Service RAG singleton (SQL → ChromaDB → Recherche sémantique)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Chargement du modèle d'embeddings
        logger.info(f"Chargement du modèle {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

        # Connexion à ChromaDB (HTTP / Docker)
        logger.info(
            f"Connexion ChromaDB {settings.CHROMA_DB_HOST}:{settings.CHROMA_DB_PORT}"
        )
        self.chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_DB_HOST,
            port=settings.CHROMA_DB_PORT,
        )
        self.collection = None

    def reload_from_db(self, db: Session):
        """Synchronise entièrement la base SQL vers ChromaDB."""
        logger.info("Synchronisation SQL → ChromaDB")

        faq_items = db.exec(select(FAQItem)).all()

        # Reset de la collection
        try:
            self.chroma_client.delete_collection(settings.CHROMA_COLLECTION_NAME)
        except Exception:
            pass  # Collection inexistante

        self.collection = self.chroma_client.create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        if not faq_items:
            logger.warning("Aucune FAQ en base")
            return

        # Préparation des données
        ids = [str(item.id) for item in faq_items]
        documents = [item.question for item in faq_items]
        metadatas = [
            {"answer": item.answer, "original_question": item.question}
            for item in faq_items
        ]

        # Génération des embeddings
        embeddings = self.model.encode(
            documents, convert_to_numpy=True
        ).tolist()

        # Insertion dans Chroma
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(f"{len(ids)} FAQ indexées")

    @staticmethod
    def normalize_query(query: str) -> str:
        """Nettoyage simple de la requête utilisateur."""
        query = re.sub(
            r"[^\w\sàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ-]",
            " ",
            query,
        )
        return re.sub(r"\s+", " ", query).strip()

    def search(self, query: str, threshold: float = 0.45) -> Dict:
        """Recherche sémantique avec règles simples et seuil de similarité."""
        clean_query = self.normalize_query(query)
        q_lower = clean_query.lower()

        # Réponses statiques
        if q_lower in {"bonjour", "hello", "salut", "hi", "bonsoir", "coucou"}:
            return {
                "answer": "Bonjour ! Comment puis-je vous aider ?",
                "confidence": 1.0,
                "provider": "static_rule",
                "matched_question": None,
            }

        if len(clean_query) < 5:
            return {
                "answer": "Pouvez-vous préciser votre question ?",
                "confidence": 0.0,
                "provider": "static_rule",
                "matched_question": None,
            }

        if not self.collection:
            return {"answer": None, "confidence": 0.0, "matched_question": None}

        # Vectorisation de la requête
        query_vec = self.model.encode(
            [clean_query], convert_to_numpy=True
        ).tolist()

        # Recherche Top-1
        results = self.collection.query(
            query_embeddings=query_vec,
            n_results=1,
        )

        if not results["ids"] or not results["ids"][0]:
            return {"answer": None, "confidence": 0.0, "matched_question": None}

        # Similarité cosinus
        distance = results["distances"][0][0]
        similarity = 1 - distance
        metadata = results["metadatas"][0][0]

        if similarity >= threshold:
            return {
                "answer": metadata["answer"],
                "confidence": similarity,
                "matched_question": metadata["original_question"],
                "faq_id": results["ids"][0][0],
            }

        # Fallback sous le seuil
        return {
            "answer": None,
            "confidence": similarity,
            "matched_question": metadata["original_question"],
        }
