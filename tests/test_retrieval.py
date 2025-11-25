import pytest
from sqlmodel import Session
from app.services.rag_engine import RAGService
from app.db.models import FAQItem

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
    assert "questions" in result["answer"]

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
    # Tester une recherche pertinente
    result = engine.search("créer compte utilisateur")
    # Le score devrait être élevé car la question est proche
    assert result["confidence"] > 0.6
    assert result["answer"] == "Allez sur la page inscription."
    assert result["faq_id"] is not None

def test_rag_search_no_match(session: Session):
    """Vérifie le comportement quand rien ne correspond."""
    engine = RAGService()
    engine.reload_from_db(session) # RAG vide maintenant
    result = engine.search("Une question qui n'a aucun sens ici")
    # Sans données, la confiance doit être 0 ou très basse
    assert result["confidence"] < 0.5
    assert result["answer"] is None