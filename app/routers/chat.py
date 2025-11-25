from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlmodel import Session, select, delete
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
    # Recherche RAG (incluant maintenant les règles statiques Bonjour/Merci)
    rag_result = rag_service.search(request.message, threshold=settings.CONFIDENCE_THRESHOLD)
    
    response_text = ""
    provider = "retrieval_only"
    confidence = rag_result["confidence"]
    matched_q = rag_result["matched_question"]
    # Si le moteur RAG a trouvé une règle statique (Bonjour), on l'utilise directement
    if rag_result.get("provider") == "static_rule":
        response_text = rag_result["answer"]
        provider = "static_rule"
        # La confiance est déjà à 1.0 grâce à la modif dans rag_engine.py
    else:
        # Décision : RAG ou LLM ?
        should_use_llm = request.use_llm and (confidence < 0.65)
        if not should_use_llm and rag_result["answer"]:
            # Cas : Réponse trouvée dans la FAQ avec une bonne confiance
            response_text = rag_result["answer"]
        else:
            # Cas : Pas de réponse FAQ ou confiance faible -> Appel LLM
            context = rag_result["answer"] if rag_result["answer"] else ""
            
            prompt = f"""Tu es un assistant support client expert.
Contexte issu de la base de connaissances : "{context}"
Question utilisateur : "{request.message}"

Instructions :
- Si le contexte répond à la question, reformule-le poliment.
- Si le contexte est vide ou non pertinent, réponds avec tes connaissances générales en restant bref.
- Réponds en français.
"""
            llm_result = await llm_orchestrator.generate_response(prompt)
            
            if llm_result["status"] == "success":
                response_text = llm_result["response"]
                provider = llm_result["provider"]
                confidence = 1.0 
                
            else:
                # Fallback ultime
                response_text = rag_result["answer"] or "Désolé, je n'ai pas la réponse et mes services IA sont indisponibles."
                provider = "fallback_error"

    # Sauvegarde
    background_tasks.add_task(
        save_interaction_task, db, request.user_id, request.message, response_text, confidence, provider
    )

    return ChatResponse(
        response=response_text,
        confidence=confidence,
        provider=provider,
        matched_question=matched_q,
        retrieval_only=(provider == "retrieval_only" or provider == "static_rule"),
        is_new_question=(rag_result["confidence"] < 0.45 and provider != "static_rule") # On marque comme "new" seulement si ce n'est pas un "Bonjour"
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