from sqlmodel import create_engine, Session
from typing import Generator
from app.core.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL, 
    echo=False,
    connect_args=connect_args
)

def get_session() -> Generator:
    with Session(engine) as session:
        yield session