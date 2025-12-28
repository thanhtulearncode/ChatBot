from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from app.db.session import get_session
from app.db.models import ChatInteraction, FAQItem
from app.core.deps import get_current_admin_user
from app.services.rag_engine import RAGService

router = APIRouter(tags=["Admin"])
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user)
):
    total_messages = db.exec(select(func.count(ChatInteraction.id))).one()
    avg_confidence = db.exec(select(func.avg(ChatInteraction.confidence))).one() or 0.0
    
    missed_questions = db.exec(
        select(ChatInteraction)
        .where(ChatInteraction.confidence < 0.45)
        .where(ChatInteraction.provider != "static_rule")
        .order_by(ChatInteraction.timestamp.desc())
        .limit(50) 
    ).all()

    stats = {
        "total_messages": total_messages,
        "avg_confidence": avg_confidence,
        "missed_questions_count": len(missed_questions),
        "recent_missed": missed_questions
    }
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
        "user": current_user,
        "active_page": "dashboard"
    })

@router.get("/faq")
async def manage_faq(
    request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user)
):
    """Affiche la liste des questions"""
    faqs = db.exec(select(FAQItem).order_by(FAQItem.id.desc())).all()
    
    return templates.TemplateResponse("admin/faq.html", {
        "request": request,
        "faqs": faqs,
        "user": current_user,
        "active_page": "faq"
    })

@router.post("/faq/add")
async def add_faq(
    request: Request,
    question: str = Form(...),
    answer: str = Form(...),
    category: str = Form("general"),
    db: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user)
):
    """Ajoute une question et recharge le RAG"""
    new_item = FAQItem(question=question, answer=answer, category=category)
    db.add(new_item)
    db.commit()
    
    RAGService().reload_from_db(db)
    
    return RedirectResponse(url="/admin/faq", status_code=303)

@router.post("/faq/delete/{faq_id}")
async def delete_faq(
    faq_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user)
):
    """Supprime une question et recharge le RAG"""
    item = db.get(FAQItem, faq_id)
    if item:
        db.delete(item)
        db.commit()
        # Rechargement du RAG après suppression
        RAGService().reload_from_db(db)
        
    return RedirectResponse(url="/admin/faq", status_code=303)

@router.get("/stats")
async def get_stats_json(db: Session = Depends(get_session), current_user = Depends(get_current_admin_user)):
    total = db.exec(select(func.count(ChatInteraction.id))).one()
    return {"total_messages": total}

@router.post("/questions/convert-to-faq/{interaction_id}")
async def convert_question_to_faq(
    interaction_id: int,
    question: str = Form(None),
    answer: str = Form(None),
    category: str = Form("general"),
    db: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user)
):
    interaction = db.get(ChatInteraction, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    faq_question = question if question else interaction.message
    faq_answer = answer if answer else interaction.response
    
    existing = db.exec(
        select(FAQItem).where(FAQItem.question == faq_question)
    ).first()
    
    if existing:
        return JSONResponse(
            status_code=400,
            content={"message": "This question already exists in FAQ", "faq_id": existing.id}
        )
    
    new_faq = FAQItem(
        question=faq_question,
        answer=faq_answer,
        category=category
    )
    db.add(new_faq)
    db.commit()
    db.refresh(new_faq)
    
    try:
        RAGService().reload_from_db(db)
    except Exception as e:
        print(f"Error reloading ChromaDB: {e}")
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Question added to FAQ successfully",
            "faq_id": new_faq.id,
            "question": new_faq.question
        }
    )

@router.get("/questions/{interaction_id}")
async def get_question_details(
    interaction_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user)
):
    interaction = db.get(ChatInteraction, interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    return {
        "id": interaction.id,
        "message": interaction.message,
        "response": interaction.response,
        "confidence": interaction.confidence,
        "provider": interaction.provider,
        "timestamp": interaction.timestamp.isoformat(),
        "user_session_id": interaction.user_session_id
    }