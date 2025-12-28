import sys
from unittest.mock import MagicMock

mock_chroma = MagicMock()
mock_chroma.HttpClient.return_value = MagicMock()  # Returns a fake client
sys.modules["chromadb"] = mock_chroma

mock_st = MagicMock()
mock_st.SentenceTransformer.return_value = MagicMock()
sys.modules["sentence_transformers"] = mock_st

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, pool
from app.main import app
from app.db.session import get_session

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=pool.StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    """Crée une nouvelle session DB pour chaque test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Crée un client HTTP de test qui utilise la DB de test."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

class MockLLM:
    async def generate_response(self, prompt):
        return {
            "response": "Ceci est une réponse simulée pour le test.",
            "provider": "mock_provider",
            "status": "success"
        }

    def get_status(self):
        return {"current": "mock", "available": ["mock"]}

@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    """Remplace automatiquement le vrai LLM par le Mock."""
    monkeypatch.setattr("app.routers.chat.llm_orchestrator", MockLLM())