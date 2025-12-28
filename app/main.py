from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse  
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel
import os

from app.core.config import settings
from app.db.session import engine, get_session
from app.services.rag_engine import RAGService
from app.routers import auth, admin, chat

templates = Jinja2Templates(directory="templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    with next(get_session()) as db:
        RAGService().reload_from_db(db)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix="/api/auth")
app.include_router(admin.router, prefix="/admin")
app.include_router(chat.router)

@app.get("/")
async def root(request: Request):
    if os.path.exists("templates/index.html"):
        return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )
    return {"message": "Erreur: templates/index.html introuvable. Vérifiez vos dossiers."}