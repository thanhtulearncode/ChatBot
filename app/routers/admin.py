from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
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
        .limit(10)
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