from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlmodel import Session, select, delete, desc
from app.db.session import get_session
from app.db.models import ChatInteraction
from app.services.rag_engine import RAGService
from app.services.llm_factory import LLMOrchestrator
from app.core.config import settings

router = APIRouter(tags=["Chat"])
rag_service = RAGService()
llm_orchestrator = LLMOrchestrator()

class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    use_llm: bool = True

class ChatResponse(BaseModel):
    response: str
    confidence: float
    provider: str
    matched_question: str | None = None
    retrieval_only: bool = False 
    is_new_question: bool = False 

def save_interaction_task(db: Session, user_id: str, msg: str, resp: str, conf: float, prov: str):
    try:
        interaction = ChatInteraction(
            user_session_id=user_id,
            message=msg,
            response=resp,
            confidence=conf,
            provider=prov
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        print(f"Erreur sauvegarde historique: {e}")

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session)
):
    history_items = db.exec(
        select(ChatInteraction)
        .where(ChatInteraction.user_session_id == request.user_id)
        .order_by(desc(ChatInteraction.timestamp))
        .limit(5)
    ).all()
    history_items = history_items[::-1]
    history_text = "\n".join(
        [f"User: {h.message}\nAssistant: {h.response}" for h in history_items]
    ) if history_items else "Aucun historique récent."

    rag_result = rag_service.search(request.message, threshold=settings.CONFIDENCE_THRESHOLD)
    response_text = ""
    provider = "retrieval_only"
    confidence = rag_result["confidence"]
    matched_q = rag_result["matched_question"]
    context_faq = rag_result["answer"] if rag_result["answer"] else ""

    if rag_result.get("provider") == "static_rule":
        return ChatResponse(
            response=rag_result["answer"],
            confidence=1.0,
            provider="static_rule",
            retrieval_only=True,
            is_new_question=False
        )
    # Cas A : Confiance TRÈS élevée -> FAQ Directe
    if context_faq and confidence >= settings.DIRECT_ANSWER_THRESHOLD:
        response_text = context_faq
        provider = "retrieval_high_confidence"
    # Cas B : Passage au LLM
    else:
        system_prompt = f"""Tu es un assistant support client utile et précis.

CONTEXTE FAQ (Peut être vide ou peu pertinent, score={confidence:.2f}) :
"{context_faq}"

HISTORIQUE :
{history_text}

INSTRUCTIONS :
1. Utilise le CONTEXTE FAQ en priorité s'il semble répondre à la question.
2. Si le contexte est vide ou hors-sujet, utilise tes connaissances.
3. Réponds toujours poliment et en français.
"""
        if request.use_llm:
            llm_result = await llm_orchestrator.generate_response(
                f"{system_prompt}\n\nUser: {request.message}"
            )
            
            if llm_result["status"] == "success":
                response_text = llm_result["response"]
                provider = f"llm_{llm_result['provider']}"
            else:
                response_text = context_faq or "Désolé, mes services d'IA sont indisponibles."
                provider = "fallback_error"
        else:
            response_text = context_faq or "Je n'ai pas trouvé de réponse exacte."

    # Sauvegarde
    background_tasks.add_task(
        save_interaction_task, db, request.user_id, request.message, response_text, confidence, provider
    )
    is_retrieval = provider in ["retrieval_high_confidence", "static_rule", "retrieval_only"]

    return ChatResponse(
        response=response_text,
        confidence=confidence,
        provider=provider,
        matched_question=matched_q,
        retrieval_only=is_retrieval,
        is_new_question=(confidence < settings.CONFIDENCE_THRESHOLD) 
    )

@router.get("/llm/status")
async def get_llm_status():
    """Retourne le statut pour le badge en haut à droite"""
    return llm_orchestrator.get_status()

@router.get("/chat/history/{user_id}")
async def get_chat_history(user_id: str, db: Session = Depends(get_session)):
    """Récupère l'historique pour un utilisateur spécifique"""
    interactions = db.exec(
        select(ChatInteraction)
        .where(ChatInteraction.user_session_id == user_id)
        .order_by(ChatInteraction.timestamp)
    ).all()
    
    history_data = []
    for i in interactions:
        history_data.append({
            "user_message": i.message,
            "bot_response": i.response,
            "confidence": i.confidence,
            "provider": i.provider,
            "retrieval_only": (i.provider == "retrieval_only")
        })
        
    return {
        "user_id": user_id,
        "total_messages": len(history_data),
        "history": history_data
    }

@router.delete("/chat/history/{user_id}")
async def clear_chat_history(user_id: str, db: Session = Depends(get_session)):
    """Efface l'historique d'un utilisateur"""
    statement = delete(ChatInteraction).where(ChatInteraction.user_session_id == user_id)
    db.exec(statement)
    db.commit()
    return {"message": f"Historique effacé pour {user_id}"}