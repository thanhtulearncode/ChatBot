from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Info App
    PROJECT_NAME: str = "Chatbot RAG Production"
    API_V1_STR: str = "/api/v1"
    # Sécurité
    SECRET_KEY: str = "CHANGE_ME_IN_PROD_PLEASE_USE_OPENSSL_RAND_HEX_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Base de données
    DATABASE_URL: str = "sqlite:///./chatbot_production.db"
    # LLM Keys
    GROQ_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    # RAG Settings
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    FAQ_JSON_PATH: str = "data/faq.json"
    CONFIDENCE_THRESHOLD: float = 0.45
    DIRECT_ANSWER_THRESHOLD: float = 0.75
    # Config Chroma
    CHROMA_DB_HOST: str = "chromadb"
    CHROMA_DB_PORT: int = 8000
    CHROMA_COLLECTION_NAME: str = "faq_collection"
    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra="ignore" 
    )

settings = Settings()