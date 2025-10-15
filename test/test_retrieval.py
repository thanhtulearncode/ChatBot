import pytest
import numpy as np
from retrieval_engine import RetrievalEngine
import json
import tempfile
import os

@pytest.fixture
def temp_faq_file():
    """Crée une FAQ temporaire"""
    faq = [
        {"id": 1, "question": "Comment créer un compte ?", "answer": "Réponse 1"},
        {"id": 2, "question": "Prix de l'abonnement ?", "answer": "Réponse 2"},
        {"id": 3, "question": "Livraison internationale ?", "answer": "Réponse 3"}
    ]
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(faq, f)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


def test_retrieval_initialization(temp_faq_file):
    """Test l'initialisation du retrieval engine"""
    engine = RetrievalEngine(
        faq_path=temp_faq_file,
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    assert len(engine.faq_data) == 3
    assert engine.question_embeddings is not None
    assert engine.question_embeddings.shape[0] == 3


def test_cosine_similarity(temp_faq_file):
    """Test le calcul de similarité cosinus"""
    engine = RetrievalEngine(temp_faq_file, "sentence-transformers/all-MiniLM-L6-v2")
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([1.0, 0.0, 0.0])
    sim = engine.cosine_similarity(vec1, vec2)
    assert abs(sim - 1.0) < 0.01  # Vecteurs identiques


def test_get_best_match(temp_faq_file):
    """Test la recherche de meilleure correspondance"""
    engine = RetrievalEngine(temp_faq_file, "sentence-transformers/all-MiniLM-L6-v2")
    result = engine.get_best_match("créer compte utilisateur")
    assert result["confidence"] > 0.3
    assert "Réponse 1" in result["answer"]
    assert result["matched_question"] is not None


def test_get_top_k_matches(temp_faq_file):
    """Test la récupération des top K résultats"""
    engine = RetrievalEngine(temp_faq_file, "sentence-transformers/all-MiniLM-L6-v2")
    results = engine.get_top_k_matches("prix livraison", k=2)
    assert len(results) == 2
    assert all("confidence" in r for r in results)
    assert results[0]["confidence"] >= results[1]["confidence"]


def test_low_confidence_response(temp_faq_file):
    """Test la gestion des requêtes sans match"""
    engine = RetrievalEngine(temp_faq_file, "sentence-transformers/all-MiniLM-L6-v2")
    result = engine.get_best_match("xyz question totalement aléatoire abc")
    assert "n'ai pas trouvé" in result["answer"].lower()
    assert result["matched_question"] is None