from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from app.db.session import get_session
from app.db.models import ChatInteraction
from app.core.deps import get_current_admin_user

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
        "user": current_user
    })

@router.get("/stats")
async def get_stats_json(
    db: Session = Depends(get_session),
    current_user = Depends(get_current_admin_user)
):
    total = db.exec(select(func.count(ChatInteraction.id))).one()
    return {"total_messages": total}