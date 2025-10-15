"""
API FastAPI avec retrieval par embeddings et mémoire.
Lancer avec : uvicorn main:app --reload
"""
import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from retrieval_engine import RetrievalEngine
from memory_manager import MemoryManager

# Config 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot")

app = FastAPI(
    title="Chatbot avec Retrieval",
    description="Bot intelligent avec embeddings et mémoire contextuelle",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Modules internes
retriever = RetrievalEngine(
    faq_path="data/faq.json",
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # Modèle français
)
memory = MemoryManager(max_history=5)

# Schemas
class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    include_context: bool = True

class ChatResponse(BaseModel):
    response: str
    confidence: float
    user_id: str
    matched_question: Optional[str] = None
    context_used: int = 0

class ConversationHistory(BaseModel):
    user_id: str
    history: List[dict]

# Routes API
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Page d’accueil de l’interface web."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Traitement d’un message utilisateur."""
    try:
        # Récupérer l'historique (désactivé temporairement)
        history = memory.get_history(request.user_id)

        # Recherche sans contexte (context_history = vide)
        result = retriever.get_best_match(
            query=request.message,
            context_history=[]
        )

        # Enregistrer l'interaction dans la mémoire
        memory.add_interaction(
            user_id=request.user_id,
            user_message=request.message,
            bot_response=result["answer"],
            confidence=result["confidence"]
        )

        return ChatResponse(
            response=result["answer"],
            confidence=result["confidence"],
            user_id=request.user_id,
            matched_question=result.get("matched_question"),
            context_used=0
        )

    except Exception as e:
        logger.exception("Erreur dans /chat : %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{user_id}", response_model=ConversationHistory)
async def get_history(user_id: str):
    """Récupérer l'historique d'un utilisateur."""
    history = memory.get_history(user_id)
    return ConversationHistory(user_id=user_id, history=history)

@app.delete("/history/{user_id}")
async def clear_history(user_id: str):
    """Effacer l'historique d'un utilisateur."""
    memory.clear_history(user_id)
    return {"message": f"Historique effacé pour {user_id}"}

@app.get("/metrics")
async def get_metrics():
    """Retourne les métriques du système."""
    return {
        "retriever": retriever.get_stats(),
        "cache": retriever.get_cache_stats(),
        "memory": memory.get_stats(),
        "index_size": len(retriever.faq_data),
    }

@app.on_event("shutdown")
async def shutdown_event():
    """Sauvegarde le cache à l'arrêt."""
    retriever.save_cache()
    logger.info("Application arrêtée proprement.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
