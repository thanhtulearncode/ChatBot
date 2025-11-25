from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import timedelta

from app.db.session import get_session
from app.db.models import User
from app.core.security import verify_password, create_access_token
from app.core.config import settings

router = APIRouter(tags=["Authentication"])
templates = Jinja2Templates(directory="templates")

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    user = _authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login")
async def login_cookie(
    request: Request,
    response: Response,
    db: Session = Depends(get_session)
):
    form = await request.form()
    email = form.get("username")
    password = form.get("password")
    
    user = _authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse("auth/login.html", {
            "request": request, 
            "error": "Identifiants incorrects"
        })
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    redirect = RedirectResponse(url="/admin/dashboard", status_code=302)
    redirect.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True, # Empêche le JS de lire le cookie (sécurité XSS)
        max_age=1800,
        samesite="lax"
    )
    return redirect

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/api/auth/login")
    response.delete_cookie("access_token")
    return response

def _authenticate_user(db: Session, email: str, password: str):
    statement = select(User).where(User.email == email)
    user = db.exec(statement).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user