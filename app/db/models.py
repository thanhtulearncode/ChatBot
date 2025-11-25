from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = True
    full_name: Optional[str] = None

class FAQItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    question: str = Field(index=True)
    answer: str
    category: str = "general"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ChatInteraction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_session_id: str = Field(index=True)  # ID anonyme du frontend
    message: str
    response: str
    confidence: float
    provider: str  # "groq", "openai", "retrieval_only"
    is_helpful: Optional[bool] = None  # Pour le feedback utilisateur
    timestamp: datetime = Field(default_factory=datetime.utcnow)