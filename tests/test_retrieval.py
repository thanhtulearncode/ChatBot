import pytest
from unittest.mock import MagicMock
from sqlmodel import Session
from app.services.rag_engine import RAGService
from app.models import FAQItem

def test_rag_static_rules():
    """Vérifie que les règles statiques (Bonjour, etc.) fonctionnent sans DB."""
    engine = RAGService()
    # Test Bonjour
    result = engine.search("Bonjour")
    assert result["confidence"] == 1.0
    assert "aider" in result["answer"]
    assert result["provider"] == "static_rule"
    # Test Merci
    result = engine.search("Merci beaucoup")
    assert result["confidence"] == 1.0
    assert result["provider"] == "static_rule"

def test_rag_search_nominal(session: Session):
    """Vérifie la recherche vectorielle avec des données en base."""
    # Peupler la base de test
    faq1 = FAQItem(question="Comment créer un compte ?", answer="Allez sur la page inscription.")
    faq2 = FAQItem(question="Quel est le prix ?", answer="C'est 10 euros.")
    session.add(faq1)
    session.add(faq2)
    session.commit()
    # Recharger le moteur RAG (synchronisation avec la DB)
    engine = RAGService()
    engine.reload_from_db(session)
    # MOCKER la collection ChromaDB pour éviter le TypeError.
    engine.collection = MagicMock()
    engine.collection.query.return_value = {
        "ids": [["1"]],
        "distances": [[0.1]],  # Doit être un float, pas un Mock
        "metadatas": [[{
            "answer": "Allez sur la page inscription.", 
            "question": "Comment créer un compte ?"
        }]],
    }
    # Tester une recherche pertinente
    result = engine.search("créer compte utilisateur")
    # Le score devrait être élevé car la question est proche
    assert result["confidence"] > 0.0
    assert result["answer"] == "Allez sur la page inscription."

def test_rag_search_no_match(session: Session):
    """Vérifie le comportement quand rien ne correspond."""
    engine = RAGService()
    engine.reload_from_db(session)
    # MOCKER la collection pour simuler une distance élevée (pas de match).
    engine.collection = MagicMock()
    engine.collection.query.return_value = {
        "ids": [["1"]],
        "distances": [[1.5]], 
        "metadatas": [[{"answer": "Réponse non pertinente"}]]
    }
    result = engine.search("Une question qui n'a aucun sens ici")
    assert result["answer"] is None
    assert result["confidence"] == 0.0