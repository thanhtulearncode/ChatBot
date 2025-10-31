"""
API FastAPI avec interface web et RAG
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import logging
import os
import json
from datetime import datetime

from retrieval_engine import RetrievalEngine
from memory_manager import MemoryManager
from llm_manager import LLMManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Chatbot RAG avec LLM Gratuit",
    description="Bot intelligent avec Retrieval + Generation",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

logger.info("🚀 Initialisation du chatbot...")

retriever = RetrievalEngine(
    faq_path="data/faq.json",
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

memory = MemoryManager(max_history=5)
llm_manager = LLMManager(preferred_provider="groq")

logger.info("✅ Chatbot initialisé avec succès!")

os.makedirs("templates", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("data", exist_ok=True)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    use_llm: bool = True


class ChatResponse(BaseModel):
    response: str
    confidence: float
    user_id: str
    matched_question: Optional[str] = None
    provider: Optional[str] = None
    retrieval_only: bool = False
    is_new_question: bool = False


def load_html_template():
    """Charge le template HTML"""
    template_path = os.path.join("templates", "index.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Template HTML non trouvé: {template_path}")
        return "<h1>Erreur: Template HTML non trouvé</h1>"


def save_new_question(question: str, answer: str, confidence: float):
    """Sauvegarde les nouvelles questions pour ajout ultérieur dans la FAQ"""
    new_questions_path = "data/new_questions.json"

    try:
        with open(new_questions_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = []

    new_question = {
        "question": question,
        "answer": answer,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat(),
        "added_to_faq": False
    }

    existing_data.append(new_question)

    with open(new_questions_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Nouvelle question sauvegardée: {question}")


@app.get("/", response_class=HTMLResponse)
async def home():
    """Interface web avec support RAG"""
    return load_html_template()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint principal avec support RAG"""
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(
                status_code=400,
                detail="Le message ne peut pas être vide"
            )

        if len(request.message.strip()) > 2000:
            raise HTTPException(
                status_code=400,
                detail="Le message est trop long (maximum 2000 caractères)"
            )

        history = memory.get_history(request.user_id)

        retrieval_result = retriever.get_best_match(
            query=request.message,
            context_history=[]
        )

        is_new_question = False

        if retrieval_result["confidence"] < 0.45:
            if request.use_llm and llm_manager.current_provider:
                llm_result = llm_manager.generate_response(
                    question=request.message,
                    context="",
                    max_tokens=300
                )

                final_response = llm_result["response"]
                provider = llm_manager.current_provider
                retrieval_only = False
                is_new_question = True

                save_new_question(
                    question=request.message,
                    answer=final_response,
                    confidence=retrieval_result["confidence"]
                )
            else:
                final_response = retrieval_result["answer"]
                provider = "retrieval_only"
                retrieval_only = True
        else:
            use_llm = (
                request.use_llm and
                retrieval_result["confidence"] > 0.4 and
                retrieval_result.get("matched_question") is not None and
                len(request.message.strip()) > 2
            )

            if use_llm:
                simple_responses = {
                    "ok", "oui", "non", "merci", "d'accord", "bien",
                    "parfait", "super", "bon", "entendu"
                }
                if request.message.lower().strip() in simple_responses:
                    use_llm = False

            if use_llm:
                llm_result = llm_manager.generate_response(
                    question=request.message,
                    context=retrieval_result["answer"],
                    max_tokens=300
                )

                final_response = llm_result["response"]
                provider = llm_result["provider"]
                retrieval_only = False
            else:
                final_response = retrieval_result["answer"]
                provider = "retrieval_only"
                retrieval_only = True

        memory.add_interaction(
            user_id=request.user_id,
            user_message=request.message,
            bot_response=final_response,
            confidence=retrieval_result["confidence"]
        )

        return ChatResponse(
            response=final_response,
            confidence=retrieval_result["confidence"],
            user_id=request.user_id,
            matched_question=retrieval_result.get("matched_question"),
            provider=provider,
            retrieval_only=retrieval_only,
            is_new_question=is_new_question
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Erreur de validation: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Erreur de validation: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Une erreur interne s'est produite. Veuillez réessayer plus tard."
        )


@app.get("/admin/new-questions")
async def get_new_questions():
    """Retourne les nouvelles questions"""
    try:
        with open("data/new_questions.json", "r", encoding="utf-8") as f:
            questions = json.load(f)
        return {"new_questions": questions}
    except FileNotFoundError:
        return {"new_questions": []}


@app.post("/admin/add-to-faq/{question_index}")
async def add_question_to_faq(question_index: int):
    """Ajoute une question à la FAQ"""
    try:
        with open("data/new_questions.json", "r", encoding="utf-8") as f:
            new_questions = json.load(f)

        if question_index < 0 or question_index >= len(new_questions):
            raise HTTPException(status_code=404, detail="Question non trouvée")

        question_data = new_questions[question_index]

        with open("data/faq.json", "r", encoding="utf-8") as f:
            faq_data = json.load(f)

        faq_data.append({
            "question": question_data["question"],
            "answer": question_data["answer"]
        })

        with open("data/faq.json", "w", encoding="utf-8") as f:
            json.dump(faq_data, f, ensure_ascii=False, indent=2)

        new_questions[question_index]["added_to_faq"] = True
        with open("data/new_questions.json", "w", encoding="utf-8") as f:
            json.dump(new_questions, f, ensure_ascii=False, indent=2)

        retriever.load_and_index()

        return {"message": "Question ajoutée à la FAQ avec succès"}

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout à la FAQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/llm/status")
async def llm_status():
    """Statut des LLMs disponibles"""
    return llm_manager.get_status()


@app.post("/llm/switch/{provider}")
async def switch_llm(provider: str):
    """Change de provider LLM"""
    success = llm_manager.switch_provider(provider)
    if success:
        return {"message": f"Provider changé vers {provider}"}
    return {"error": f"Provider {provider} non disponible"}


@app.get("/metrics")
async def get_metrics():
    """Métriques du système"""
    return {
        "retriever": retriever.get_stats(),
        "memory": memory.get_stats(),
        "llm": llm_manager.get_status(),
        "index_size": len(retriever.faq_data)
    }


@app.get("/health")
async def health_check():
    """Vérification de l'état du service"""
    return {
        "status": "healthy",
        "retriever": "loaded" if retriever.faq_data else "not_loaded",
        "llm": llm_manager.current_provider
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
